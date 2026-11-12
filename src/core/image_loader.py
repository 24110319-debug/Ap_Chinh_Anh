"""Safe OpenCV image I/O, including paths containing Vietnamese characters."""
from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np


def load_image(path: str) -> np.ndarray:
    """Read an image through NumPy bytes so Unicode Windows paths work reliably."""
    data = np.fromfile(Path(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError("Không thể đọc tệp ảnh này.")
    return image


def save_image(path: str, image: np.ndarray) -> None:
    """Encode then write bytes, preserving Unicode paths and the chosen extension."""
    suffix = Path(path).suffix.lower() or ".png"
    ok, encoded = cv2.imencode(suffix, image)
    if not ok:
        raise ValueError("Định dạng ảnh không được hỗ trợ.")
    encoded.tofile(Path(path))

