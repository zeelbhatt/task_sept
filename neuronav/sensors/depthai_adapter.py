import os
import time
from datetime import datetime
from typing import Optional, Union

from ..utils.installer import ensure_package

class DepthAISensor:
    """
    Adapter that prefers a real Luxonis OAK (via depthai) but can fall back to:
      - webcam (cv2.VideoCapture(index))
      - synthetic frames (generated with numpy)
    This lets you test without hardware.
    """

    def __init__(
        self,
        model: str = "oak-d-pro",
        output_dir: str = "recordings",
        allow_mock_on_no_device: bool = True,
        mock_source: Union[int, str] = 0,  # 0 = default webcam; 'synthetic' for generated frames
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
    ):
        self.name = model
        self.output_dir = output_dir
        self._pipeline = None
        self._device = None
        self._rgb_queue = None
        self._video_writer = None
        self._running = False
        self._fps = fps
        self._width = width
        self._height = height

        self.allow_mock_on_no_device = allow_mock_on_no_device
        self.mock_source = mock_source
        self._mode = "depthai"     # 'depthai' | 'webcam' | 'synthetic'
        self._cap = None           # for webcam
        self._current_filepath = None

        # We always need OpenCV for writing video (and webcam)
        if not ensure_package("opencv-python", "cv2"):
            # optional fallback to headless on servers
            if not ensure_package("opencv-python-headless", "cv2"):
                raise RuntimeError(
                    "OpenCV is required for recording video. "
                    "Please install: pip install opencv-python"
                )
        import cv2  # safe now
        self._cv2 = cv2

        # DepthAI is optional if we're mocking
        self._has_depthai = ensure_package("depthai", "depthai")
        if self._has_depthai:
            import depthai as dai  # safe now
            self._dai = dai
        else:
            if not self.allow_mock_on_no_device:
                raise RuntimeError(
                    "DepthAI is not installed and mocking is disabled. "
                    "Install: pip install depthai  OR enable allow_mock_on_no_device=True"
                )
            self._mode = "webcam" if isinstance(self.mock_source, int) else "synthetic"

    def _set_mode_based_on_devices(self):
        """
        Decide whether to use real depthai or fallback.
        """
        if not self._has_depthai:
            # already decided in __init__
            return
        try:
            devices = self._dai.Device.getAllAvailableDevices()
            if devices:
                self._mode = "depthai"
            else:
                if self.allow_mock_on_no_device:
                    self._mode = "webcam" if isinstance(self.mock_source, int) else "synthetic"
                    print("[neuronav] No OAK device detected. Falling back to mock:", self._mode)
                else:
                    raise RuntimeError("No OAK device detected and mocking is disabled.")
        except Exception as e:
            if self.allow_mock_on_no_device:
                self._mode = "webcam" if isinstance(self.mock_source, int) else "synthetic"
                print(f"[neuronav] Could not query OAK devices ({e}). Falling back to mock: {self._mode}")
            else:
                raise

    def initialize(self) -> None:
        os.makedirs(self.output_dir, exist_ok=True)

        # Decide capture mode
        self._set_mode_based_on_devices()

        if self._mode == "depthai":
            dai = self._dai
            pipeline = dai.Pipeline()

            cam = pipeline.create(dai.node.ColorCamera)
            cam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
            cam.setFps(self._fps)
            cam.setIspScale(1, 2)  # 1080p → 720p
            cam.setVideoSize(self._width, self._height)

            xout = pipeline.create(dai.node.XLinkOut)
            xout.setStreamName("video")
            cam.video.link(xout.input)

            self._pipeline = pipeline
        else:
            # webcam / synthetic: no pipeline needed
            self._pipeline = None

    def _open_writer(self) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        mode_tag = self._mode
        filename = f"{ts}_{self.name.replace('-', '_')}_{mode_tag}.mp4"
        filepath = os.path.join(self.output_dir, filename)

        fourcc = self._cv2.VideoWriter_fourcc(*"mp4v")
        self._video_writer = self._cv2.VideoWriter(
            filepath, fourcc, self._fps, (self._width, self._height)
        )
        if not self._video_writer.isOpened():
            raise RuntimeError("Failed to open video writer.")
        self._current_filepath = filepath
        print(f"[neuronav] Recording to {filepath}")
        return filepath

    def start(self) -> None:
        if self._mode == "depthai":
            dai = self._dai
            try:
                self._device = dai.Device(self._pipeline)
            except Exception as e:
                if self.allow_mock_on_no_device:
                    print(f"[neuronav] DepthAI start failed ({e}). Falling back to mock.")
                    self._mode = "webcam" if isinstance(self.mock_source, int) else "synthetic"
                else:
                    raise

        if self._mode == "depthai":
            self._rgb_queue = self._device.getOutputQueue(name="video", maxSize=8, blocking=False)
            self._open_writer()
            self._running = True
            return

        # Mock modes
        if self._mode == "webcam":
            self._cap = self._cv2.VideoCapture(self.mock_source)
            # Try to set desired resolution/fps (may be ignored by some webcams)
            self._cap.set(self._cv2.CAP_PROP_FRAME_WIDTH, self._width)
            self._cap.set(self._cv2.CAP_PROP_FRAME_HEIGHT, self._height)
            self._cap.set(self._cv2.CAP_PROP_FPS, self._fps)
            if not self._cap.isOpened():
                raise RuntimeError("Failed to open webcam. Try a different index (e.g., 1) or use mock_source='synthetic'.")
            self._open_writer()
            self._running = True
            return

        if self._mode == "synthetic":
            # nothing to open; frames generated in read()
            self._open_writer()
            self._running = True
            return

    def read(self):
        """
        Pull a frame and write to file.
        Return True if wrote a frame, False if nothing was available yet.
        """
        if not self._running:
            return False

        if self._mode == "depthai":
            pkt = self._rgb_queue.tryGet()
            if pkt is None:
                return False
            frame = pkt.getCvFrame()
            self._video_writer.write(frame)
            return True

        if self._mode == "webcam":
            ok, frame = self._cap.read()
            if not ok:
                time.sleep(0.005)
                return False
            # Optionally resize to target shape (some cams ignore set())
            if frame.shape[1] != self._width or frame.shape[0] != self._height:
                frame = self._cv2.resize(frame, (self._width, self._height))
            self._video_writer.write(frame)
            return True

        if self._mode == "synthetic":
            # Generate a simple moving test pattern
            import numpy as np
            frame = np.zeros((self._height, self._width, 3), dtype=np.uint8)
            t = time.time()
            # moving bars
            x = int((t*100) % self._width)
            frame[:, x:x+40, :] = 255
            # timestamp overlay
            txt = datetime.now().strftime("%H:%M:%S")
            self._cv2.putText(frame, f"SYNTH {txt}", (20, 50),
                              self._cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255,255,255), 2, self._cv2.LINE_AA)
            self._video_writer.write(frame)
            time.sleep(1.0 / max(1, self._fps))  # pace to fps
            return True

        return False

    def stop(self) -> None:
        self._running = False

    def cleanup(self) -> None:
        # Release resources in reverse order
        if self._video_writer is not None:
            self._video_writer.release()
            self._video_writer = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        if self._device is not None:
            try:
                self._device.close()
            except Exception:
                pass
            self._device = None
        print("[neuronav] Cleanup complete.")
