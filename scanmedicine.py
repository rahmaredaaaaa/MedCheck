import os
import tempfile
import time

import cv2


class CameraError(Exception):
    pass


class CameraStream:
    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self._capture = None

    def open(self):
        self._capture = cv2.VideoCapture(
            self.camera_index,
            cv2.CAP_MSMF
        )

        if self._capture is None or not self._capture.isOpened():
            self._capture = None
            raise CameraError(
                "Unable to access camera. Please check camera permissions."
            )

        for _ in range(10):
            success, frame = self._capture.read()

            if success and frame is not None:
                return self

            time.sleep(0.1)

        self._capture.release()
        self._capture = None

        raise CameraError(
            "Camera opened but no image could be captured."
        )

    def is_open(self) -> bool:
        return (
            self._capture is not None
            and self._capture.isOpened()
        )

    def read_frame(self):
        if not self.is_open():
            return None

        success, frame = self._capture.read()

        if not success or frame is None:
            return None

        return frame

    def release(self):
        if self._capture is not None:
            try:
                self._capture.release()
            finally:
                self._capture = None


def save_frame_to_temp_file(frame) -> str:
    if frame is None:
        raise CameraError("Unable to capture image.")

    temp_dir = os.path.join(
        tempfile.gettempdir(),
        "medcheck_captures"
    )

    os.makedirs(temp_dir, exist_ok=True)

    file_name = f"capture_{int(time.time() * 1000)}.jpg"

    file_path = os.path.join(
        temp_dir,
        file_name
    )

    success = cv2.imwrite(
        file_path,
        frame
    )

    if not success:
        raise CameraError(
            "Unable to save captured image."
        )

    return file_path