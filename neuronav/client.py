import time
from typing import Optional
from .sensors.base import Sensor

class NeuronavClient:
    def __init__(self, api_key: str, upload: bool = False):
        """
        For v1, we just store the api_key. 'upload' is a placeholder for future cloud sync.
        """
        if not isinstance(api_key, str) or not api_key:
            raise ValueError("api_key must be a non-empty string.")
        self.api_key = api_key
        self.upload = upload

    def record(self, sensor: Sensor, duration_seconds: Optional[int] = None):
        """
        Start recording. If duration_seconds is None, run until Ctrl+C.
        """
        try:
            sensor.start()
            start = time.time()
            while True:
                sensor.read()  # write frames if available
                if duration_seconds is not None and (time.time() - start) >= duration_seconds:
                    break
        except KeyboardInterrupt:
            print("\n[neuronav] Stopping recording (KeyboardInterrupt).")
        finally:
            sensor.stop()
            sensor.cleanup()
            print("[neuronav] Recording finished.")
