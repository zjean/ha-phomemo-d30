"""Test the Phomemo D30 protocol encoding."""
import pytest
from PIL import Image

from custom_components.phomemo_d30.phomemo.protocol import (
    preprocess_image,
    encode_print_command,
    get_initialization_packets,
)


def test_get_initialization_packets():
    """Test that initialization packets are returned correctly."""
    packets = get_initialization_packets()

    assert len(packets) == 7
    assert all(isinstance(p, bytes) for p in packets)
    # Verify first packet
    assert packets[0] == bytes.fromhex('1f1138')
    # Verify last packet
    assert packets[6] == bytes.fromhex('1f110a1f110202')


def test_preprocess_image_portrait():
    """Test image preprocessing for portrait orientation."""
    # Create a portrait test image (height > width)
    img = Image.new("RGB", (100, 200), color="white")

    # Preprocess should resize to 96 width and convert to 1-bit
    processed = preprocess_image(img)

    assert processed.mode == "1"  # 1-bit black/white
    assert processed.width == 96  # Resized to D30 width
    # Height should maintain aspect ratio (floor(96 / (100/200)) = floor(96 / 0.5) = floor(192))
    assert processed.height == 192


def test_preprocess_image_landscape():
    """Test image preprocessing for landscape orientation (no rotation in polskafan)."""
    # Create a landscape test image (width > height)
    img = Image.new("RGB", (200, 100), color="white")

    # Preprocess should resize to 96 width (no rotation)
    processed = preprocess_image(img)

    assert processed.mode == "1"  # 1-bit black/white
    assert processed.width == 96  # Resized to D30 width
    # Height should maintain aspect ratio (floor(96 / (200/100)) = floor(96 / 2) = 48)
    assert processed.height == 48


def test_preprocess_image_already_96():
    """Test image preprocessing when already at target width."""
    # Create image already at 96 width
    img = Image.new("RGB", (96, 100), color="white")

    processed = preprocess_image(img)

    assert processed.mode == "1"
    assert processed.width == 96
    # Height should maintain aspect ratio (floor(96 / (96/100)) = floor(100))
    assert processed.height == 100


def test_encode_print_command():
    """Test encoding a print command with image data."""
    # Create a simple 1-bit test image (must be mode '1')
    img = Image.new("1", (96, 100), color=1)  # 96x100 white image

    # Encode the print command (returns list of commands)
    commands = encode_print_command(img)

    # Should return list
    assert isinstance(commands, list)
    assert len(commands) > 0

    # First command should be bytes
    assert isinstance(commands[0], bytes)

    # Should start with the polskafan print command header
    assert commands[0].startswith(bytes.fromhex('1f1124001b401d7630000c004001'))

    # Should contain image data (96/8 = 12 bytes per line * 100 lines = 1200 bytes)
    # Plus header (14 bytes) = 1214 bytes
    assert len(commands[0]) == 1214


def test_encode_print_command_requires_mode_1():
    """Test that encode_print_command requires mode '1' image."""
    # Create an RGB image (wrong mode)
    img = Image.new("RGB", (96, 100), color="white")

    # Should raise ValueError for wrong mode
    with pytest.raises(ValueError, match="Image must be in mode '1'"):
        encode_print_command(img)


def test_encode_print_command_chunks_large_image():
    """Test that large images are properly chunked (>255 lines)."""
    # Create a tall image that will require multiple chunks
    img = Image.new("1", (96, 512), color=1)  # 512 lines = 3 chunks (255+255+2)

    commands = encode_print_command(img)

    # Should return 3 commands (one per chunk)
    assert len(commands) == 3

    # Each command should start with the print header
    for cmd in commands:
        assert cmd.startswith(bytes.fromhex('1f1124001b401d7630000c004001'))


def test_encode_print_command_exact_chunk_boundary():
    """Test image exactly at chunk boundary (255 lines)."""
    img = Image.new("1", (96, 255), color=1)

    commands = encode_print_command(img)

    # Should return exactly 1 command
    assert len(commands) == 1


def test_encode_print_command_two_chunks():
    """Test image requiring exactly 2 chunks (256 lines)."""
    img = Image.new("1", (96, 256), color=1)

    commands = encode_print_command(img)

    # Should return 2 commands (255 + 1)
    assert len(commands) == 2
