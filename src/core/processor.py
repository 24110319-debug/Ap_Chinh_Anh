"""Pure OpenCV image operations used by the user interface."""
from __future__ import annotations

import cv2
import numpy as np


class ImageProcessor:
    """Collection of stateless, testable image-processing operations."""

    @staticmethod
    def grayscale(image: np.ndarray) -> np.ndarray:
        """Convert a BGR/BGRA image to a single-channel grayscale image."""
        if image.ndim == 2:
            return image.copy()
        code = cv2.COLOR_BGRA2GRAY if image.shape[2] == 4 else cv2.COLOR_BGR2GRAY
        return cv2.cvtColor(image, code)

    @staticmethod
    def canny(image: np.ndarray, threshold1: int, threshold2: int) -> np.ndarray:
        """Return an edge map after converting the input to grayscale."""
        low, high = sorted((int(threshold1), int(threshold2)))
        return cv2.Canny(ImageProcessor.grayscale(image), low, high)

    @staticmethod
    def crop(image: np.ndarray, x: int, y: int, width: int, height: int) -> np.ndarray:
        """Crop a rectangular region, validating that it stays inside the image."""
        h, w = image.shape[:2]
        x, y, width, height = int(x), int(y), int(width), int(height)
        if width <= 0 or height <= 0 or x < 0 or y < 0 or x + width > w or y + height > h:
            raise ValueError("Vùng cắt phải nằm hoàn toàn trong ảnh và có kích thước dương.")
        return image[y:y + height, x:x + width].copy()

    @staticmethod
    def resize(image: np.ndarray, width: int, height: int) -> np.ndarray:
        """Resize to exact dimensions; choose interpolation suited to scaling direction."""
        width, height = int(width), int(height)
        if width <= 0 or height <= 0:
            raise ValueError("Chiều rộng và chiều cao phải lớn hơn 0.")
        old_h, old_w = image.shape[:2]
        interpolation = cv2.INTER_AREA if width < old_w or height < old_h else cv2.INTER_CUBIC
        return cv2.resize(image, (width, height), interpolation=interpolation)

    @staticmethod
    def negative(image: np.ndarray) -> np.ndarray:
        """Create a photographic negative without corrupting PNG transparency.

        OpenCV stores colour images as BGR/BGRA.  For gray and BGR images the
        inverse is exactly ``255 - pixel``.  A BGRA image needs special care:
        its alpha channel is transparency rather than colour, so inverting it
        makes transparent pixels opaque (and can make a PNG preview appear
        incorrect).  Therefore only B, G and R are inverted in that case.
        """
        if image is None or image.size == 0:
            raise ValueError("Ảnh đầu vào trống.")
        if image.dtype != np.uint8:
            raise ValueError("Ảnh phải có định dạng điểm ảnh uint8.")

        if image.ndim == 3 and image.shape[2] == 4:
            result = image.copy()
            result[:, :, :3] = 255 - result[:, :, :3]
            return result

        return 255 - image

    @staticmethod
    def logarithmic(image: np.ndarray, coefficient: float = 45.99) -> np.ndarray:
        """Enhance dark detail using the adjustable equation ``s = c * log(1 + r)``.

        The default coefficient is approximately ``255 / log(256)``, which
        maps a white input back to white. Smaller values darken the result;
        higher values brighten it and may clip highlights to 255.
        """
        coefficient = float(coefficient)
        if coefficient <= 0:
            raise ValueError("Hệ số Logarit phải lớn hơn 0.")
        transformed = coefficient * np.log1p(image.astype(np.float32))
        return np.clip(transformed, 0, 255).astype(np.uint8)

    @staticmethod
    def gamma(image: np.ndarray, gamma_value: float) -> np.ndarray:
        """Apply gamma correction through a lookup table (gamma > 1 brightens)."""
        gamma_value = float(gamma_value)
        if gamma_value <= 0:
            raise ValueError("Gamma phải lớn hơn 0.")
        table = np.array([((value / 255.0) ** (1.0 / gamma_value)) * 255
                          for value in range(256)], dtype=np.uint8)
        return cv2.LUT(image, table)

