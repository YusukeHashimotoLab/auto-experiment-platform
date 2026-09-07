"""Helper for recording overhead-camera video in the background.

Controlled with start() / stop() by the workflow executor (or any caller);
saves an mp4 file that runs alongside a synthesis-workflow execution.
"""
from __future__ import annotations

import logging
import os
import platform
import threading
import time
from typing import Optional

import cv2

logger = logging.getLogger(__name__)


def _platform_backend() -> int:
    """Return the best VideoCapture backend for the current OS."""
    os_name = platform.system()
    if os_name == "Windows":
        return cv2.CAP_MSMF
    if os_name == "Linux":
        return cv2.CAP_V4L2
    if os_name == "Darwin":
        return cv2.CAP_AVFOUNDATION
    return cv2.CAP_ANY


class VideoRecorder:
    """OpenCV-based continuous recording thread."""

    def __init__(
        self,
        output_path: str,
        camera_index: int = 1,
        width: int = 1280,
        height: int = 720,
        fps: float = 30.0,
        fourcc: str = "mp4v",
    ):
        self.output_path = output_path
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self.fourcc = fourcc

        self._cap: Optional[cv2.VideoCapture] = None
        self._writer: Optional[cv2.VideoWriter] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._frames_written = 0

    def start(self) -> bool:
        """Open the camera and start the recording thread. Returns False on failure."""
        cap = cv2.VideoCapture(self.camera_index, _platform_backend())
        if not cap.isOpened():
            logger.error(f"Could not open video camera index={self.camera_index}")
            return False

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cam_fps = cap.get(cv2.CAP_PROP_FPS)
        if cam_fps and cam_fps > 1.0:
            self.fps = float(cam_fps)

        os.makedirs(os.path.dirname(self.output_path) or ".", exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*self.fourcc)
        writer = cv2.VideoWriter(self.output_path, fourcc, self.fps, (actual_w, actual_h))
        if not writer.isOpened():
            cap.release()
            logger.error(f"Could not open VideoWriter: {self.output_path}")
            return False

        self._cap = cap
        self._writer = writer
        self._stop.clear()
        self._frames_written = 0
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info(
            f"Started video recording: {self.output_path} "
            f"({actual_w}x{actual_h} @ {self.fps:.1f}fps, fourcc={self.fourcc})"
        )
        return True

    def _loop(self):
        period = 1.0 / max(self.fps, 1.0)
        next_tick = time.monotonic()
        while not self._stop.is_set():
            ok, frame = self._cap.read()
            if not ok:
                time.sleep(0.01)
                continue
            self._writer.write(frame)
            self._frames_written += 1
            # pacing to approximate a constant frame rate
            next_tick += period
            sleep_for = next_tick - time.monotonic()
            if sleep_for > 0:
                time.sleep(sleep_for)
            else:
                next_tick = time.monotonic()

    def stop(self) -> Optional[str]:
        """Stop recording and return the saved path. Returns None if never started."""
        if self._thread is None:
            return None
        self._stop.set()
        self._thread.join(timeout=5.0)
        if self._writer is not None:
            self._writer.release()
        if self._cap is not None:
            self._cap.release()
        logger.info(
            f"Stopped video recording: {self.output_path} ({self._frames_written} frames)"
        )
        self._thread = None
        self._writer = None
        self._cap = None
        return self.output_path
