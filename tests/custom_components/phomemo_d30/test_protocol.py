"""Test the Phomemo D30 protocol encoding."""
import pytest
from PIL import Image

from custom_components.phomemo_d30.phomemo.protocol import (
    preprocess_image,
    encode_print_command,
)


def test_preprocess_image_portrait():
    """Test image preprocessing for portrait orientation (no rotation)."""
    # Create a portrait test image (height > width)
    img = Image.new("RGB", (100, 200), color="white")

    # Preprocess should resize to 384 width and convert to 1-bit
    processed = preprocess_image(img)

    assert processed.mode == "1"  # 1-bit black/white
    assert processed.width == 384  # Resized to D30 width
    # Height should maintain aspect ratio (200/100 * 384 = 768)
    assert processed.height == 768


def test_preprocess_image_landscape():
    """Test image preprocessing for landscape orientation (auto-rotate)."""
    # Create a landscape test image (width > height)
    img = Image.new("RGB", (200, 100), color="white")

    # Preprocess should rotate, then resize to 384 width
    processed = preprocess_image(img)

    assert processed.mode == "1"  # 1-bit black/white
    assert processed.width == 384  # Resized to D30 width
    # After rotation (100x200) and resize, height should be 200/100 * 384 = 768
    assert processed.height == 768


def test_preprocess_image_already_384():
    """Test image preprocessing when already at target width (portrait)."""
    # Create portrait image already at 384 width (height > width, so no rotation)
    img = Image.new("RGB", (384, 500), color="white")

    processed = preprocess_image(img)

    assert processed.mode == "1"
    assert processed.width == 384
    assert processed.height == 500  # Height unchanged (no resize needed)


def test_encode_print_command():
    """Test encoding a print command with image data."""
    # Create a simple 1-bit test image (must be mode '1')
    img = Image.new("1", (384, 100), color=1)  # 384x100 white image

    # Encode the print command
    data = encode_print_command(img)

    # Should return bytes
    assert isinstance(data, bytes)

    # Should contain data
    assert len(data) > 0

    # Should start with the Phomemo header
    assert data.startswith(b'\x1b\x40\x1b\x61\x01\x1f\x11\x02\x04')

    # Should contain marker block with magic value 0x1d76 (little-endian)
    assert b'\x1d\x76' in data

    # Should end with footer sequences
    assert b'\x1b\x64\x02' in data  # Feed command
    assert data.endswith(b'\x1f\x11\x09')  # Final control sequence


def test_encode_print_command_requires_mode_1():
    """Test that encode_print_command requires mode '1' image."""
    # Create an RGB image (wrong mode)
    img = Image.new("RGB", (384, 100), color="white")

    # Should raise ValueError for wrong mode
    with pytest.raises(ValueError, match="Image must be in mode '1'"):
        encode_print_command(img)


def test_encode_print_command_chunks_large_image():
    """Test that large images are properly chunked (>256 lines)."""
    # Create a tall image that will require multiple chunks
    img = Image.new("1", (384, 512), color=1)  # 512 lines = 2 chunks

    data = encode_print_command(img)

    # Should contain two marker blocks (one per chunk)
    # Each marker starts with 0x1d76
    marker_count = data.count(b'\x1d\x76')
    assert marker_count == 2  # Two chunks for 512 lines


def test_line_feed_byte_substitution():
    """Test that 0x0a bytes are substituted with 0x14."""
    # Create a specific pattern that would generate 0x0a bytes
    # This is a regression test for the critical bug fix
    img = Image.new("1", (8, 1), color=1)  # 8 pixels = 1 byte per line

    # Set pixels to create byte pattern 0x0a (00001010 in binary)
    # Bit 0 (MSB): white, Bit 1: white, Bit 2: white, Bit 3: white
    # Bit 4: black, Bit 5: white, Bit 6: black, Bit 7: white
    img.putpixel((4, 0), 0)  # Black
    img.putpixel((6, 0), 0)  # Black

    data = encode_print_command(img)

    # The line data should NOT contain 0x0a
    assert b'\x0a' not in data or data.count(b'\x0a') == 0

    # If the pattern would have created 0x0a, it should now be 0x14
    # Note: This is hard to test directly without knowing the exact data structure
    # But we can verify 0x0a doesn't appear in image data sections
