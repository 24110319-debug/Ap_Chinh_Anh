"""Conversions between OpenCV arrays and Tkinter-compatible Pillow images."""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image, ImageTk


def cv_to_pil(image: np.ndarray) -> Image.Image:
    """Convert OpenCV BGR/BGRA/grayscale arrays to a correctly coloured PIL image."""
    if image.ndim == 2:
        return Image.fromarray(image)
    if image.shape[2] == 4:
        return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA))
    return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))


def fit_image(image: np.ndarray, max_width: int, max_height: int) -> tuple[ImageTk.PhotoImage, float]:
    """Create a PhotoImage that fits an area and return its display scale."""
    pil = cv_to_pil(image)
    scale = min(max_width / pil.width, max_height / pil.height, 1.0)
    size = (max(1, int(pil.width * scale)), max(1, int(pil.height * scale)))
    return ImageTk.PhotoImage(pil.resize(size, Image.Resampling.LANCZOS)), scale

