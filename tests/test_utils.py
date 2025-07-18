"""Unit tests for pdf2text.utils helper functions."""
from PIL import Image

from pdf2text.utils import enhance_image


def test_enhance_image_returns_grayscale_and_same_size():
    """enhance_image should return a grayscale image with unchanged dimensions."""
    img = Image.new("RGB", (80, 60), color="white")

    enhanced = enhance_image(img)

    # Image mode should now be grayscale ("L")
    assert enhanced.mode == "L"
    # Dimensions must stay the same
    assert enhanced.size == img.size
