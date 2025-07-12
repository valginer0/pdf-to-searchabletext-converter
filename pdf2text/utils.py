"""Utility helpers for pdf2text."""

from __future__ import annotations

from PIL import Image, ImageEnhance, ImageFilter


def enhance_image(image: Image.Image, contrast: float = 2.0, sharpness: float = 2.0) -> Image.Image:
    """Return an enhanced grayscale image for better OCR.

    Parameters
    ----------
    image : PIL.Image.Image
        Source image.
    contrast, sharpness : float
        Enhancement factors. 1.0 leaves the image unchanged.
    """
    gray = image.convert("L")

    gray = ImageEnhance.Contrast(gray).enhance(contrast)
    gray = ImageEnhance.Sharpness(gray).enhance(sharpness)
    gray = gray.filter(ImageFilter.MedianFilter())
    return gray
