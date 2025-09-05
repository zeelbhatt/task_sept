import os
import time
from datetime import datetime
from typing import Optional

from ..utils.installer import ensure_package

class MockSensor:
    """
    Records from a video file (cv2.VideoCapture) if provided,
    otherwise generates synthetic frames. Lets you test NeuronavClient.record()
    without any hardware.
    """
    def __init__(self, source: Optional[str] = None, output_dir: str = "recordings"):
        self.name = "mock"
        self.source = source  # path to .mp4 or None
        self.output_dir = output_dir
        self._cap = None
        self._video_writer = None
        self._running = False
        self._fps = 30
        self._width = 1280
        self._height = 720

        # Ensure OpenCV
        if not ensure_package("opencv-python", "cv2"):
            raise RuntimeError(
                "OpenCV is required for mock recording. Install: pip install opencv-python"
            )
        import cv2
        self._cv2 = cv2

    def initialize(self) -> None:
        os.makedirs(self.output_dir, exist_ok=True)
        if self.source:
            self._cap = self._cv2.VideoCapture(self.source)
            if not self._cap.isOpened():
                raise RuntimeError(f"Failed to open mock source: {self.source}")

    def start(self) -> None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ts}_{self.name}.mp4"
        self._current_filepath = os.path.join(self.output_dir, filename)

        fourcc = self._cv2.VideoWriter_fourcc(*"mp4v")
        self._video_writer = self._cv2.VideoWriter(
            self._current_filepath, fourcc, self._fps, (self._width, self._height)
        )
        if not self._video_writer.isOpened():
            raise RuntimeError("Failed to open video writer.")
        self._running = True
        print(f"[neuronav] (mock) Recording to {self._current_filepath}")

    def _next_frame(self):
        if self._cap is not None:
            ok, frame = self._cap.read()
            if not ok:
                # loop the video
                self._cap.set(self._cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self._cap.read()
            return frame
        # synthetic frame
        import numpy as np
        if not ensure_package("numpy", "numpy"):
            raise RuntimeError("numpy required for mock frames.")
        t = int(time.time() * 10)
        frame = (np.ones((self._height, self._width, 3), dtype=np.uint8) * 40)
        self._cv2.putText(frame, f"MOCK {t}", (50, 100),
                          self._cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
        return frame

    def read(self):
        if not self._running:
            return False
        frame = self._next_frame()
        if frame is None:
            return False
        self._video_writer.write(frame)
        # simulate fps
        time.sleep(1.0 / self._fps)
        return True

    def stop(self) -> None:
        self._running = False

    def cleanup(self) -> None:
        if self._video_writer is not None:
            self._video_writer.release()
            self._video_writer = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        print("[neuronav] Cleanup complete.")
