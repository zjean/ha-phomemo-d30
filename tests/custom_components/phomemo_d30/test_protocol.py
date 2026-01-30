"""Test the Phomemo D30 protocol encoding."""
import pytest
from PIL import Image

from custom_components.phomemo_d30.phomemo.protocol import (
    preprocess_image,
    encode_print_command,
)


def test_preprocess_image():
    """Test image preprocessing for D30 printer."""
    # Create a test image (RGB color)
    img = Image.new("RGB", (100, 50), color="white")

    # Preprocess should convert to 1-bit black/white and rotate 90 degrees
    processed = preprocess_image(img)

    assert processed.mode == "1"  # 1-bit black/white
    assert processed.size == (50, 100)  # Rotated 90 degrees (swapped dimensions)


def test_encode_print_command():
    """Test encoding a print command with image data."""
    # Create a simple 1-bit test image
    img = Image.new("1", (16, 8), color=1)  # 16x8 white image

    # Encode the print command
    data = encode_print_command(img)

    # Should return bytes
    assert isinstance(data, bytes)

    # Should contain initialization and print commands
    assert len(data) > 0

    # Should contain printer init sequence (1f112400) and ESC @ (1b40)
    assert b'\x1f\x11\x24\x00' in data  # Printer init
    assert b'\x1b\x40' in data  # ESC @

    # Should contain GS v 0 command (1d7630)
    assert b'\x1d\x76\x30' in data  # GS v 0
