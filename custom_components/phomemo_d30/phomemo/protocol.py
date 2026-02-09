"""Phomemo D30 protocol encoding.

This module handles image preprocessing and protocol encoding for the Phomemo D30 printer.
Adapted from polskafan/phomemo_d30 (https://github.com/polskafan/phomemo_d30).

Licensed under GPL-3.0, compatible with the project's GPL-3.0 license.
"""

from io import BytesIO
import math
from PIL import Image, ImageOps


def preprocess_image(image: Image.Image, target_width: int = 96) -> Image.Image:
    """Preprocess image for D30 printer.

    The D30 printer expects:
    - Resize to 96 pixels width maintaining aspect ratio
    - Invert colors then convert to 1-bit black/white

    Args:
        image: Input PIL Image in any mode (RGB, RGBA, L, etc.)
        target_width: Target width in dots (default: 96 for D30)

    Returns:
        Preprocessed PIL Image in mode '1' (1-bit black/white)
    """
    # Resize to target width while maintaining aspect ratio
    src_w, src_h = image.size
    aspect = src_w / src_h
    new_size = (target_width, math.floor(target_width / aspect))
    resized = image.resize(new_size, Image.Resampling.LANCZOS)

    # Invert, convert to RGB, then to 1-bit (matching polskafan's implementation)
    converted = ImageOps.invert(resized.convert("RGB")).convert("1")

    return converted


def get_initialization_packets() -> list[bytes]:
    """Get initialization packets for D30 printer.

    These packets were sniffed from Android app "Print Master".
    Must be sent before each print command.

    Returns:
        List of initialization packet bytes
    """
    packets = [
        '1f1138',
        '1f11121f1113',
        '1f1109',
        '1f1111',
        '1f1119',
        '1f1107',
        '1f110a1f110202'
    ]
    return [bytes.fromhex(packet) for packet in packets]


def encode_print_command(image: Image.Image, threshold: int = 127) -> list[bytes]:
    """Encode a complete print command for the D30 printer.

    This function creates the complete byte sequence to send to the printer,
    using the proprietary Phomemo protocol discovered by packet sniffing from
    the Android "Print Master" app.

    Args:
        image: PIL Image in mode '1' (1-bit black/white)
        threshold: Pixel brightness threshold for binary conversion (0-255)

    Returns:
        List of byte sequences to send to printer (one per chunk)

    Raises:
        ValueError: If image is not in mode '1'
    """
    if image.mode != '1':
        raise ValueError(f"Image must be in mode '1' (1-bit), got '{image.mode}'")

    width = image.width
    commands = []

    # Split image into chunks of max 255 lines each
    for chunk in _split_image(image, max_height=255):
        # Start with print command header (sniffed from Print Master app)
        output = bytearray.fromhex('1f1124001b401d7630000c004001')

        # Convert chunk to bits
        bits = _image_to_bits(chunk, threshold)

        # Encode each line
        for line in bits:
            for byte_num in range(width // 8):
                byte_value = 0
                for bit in range(8):
                    pixel = line[byte_num * 8 + bit]
                    byte_value |= (pixel & 0x01) << (7 - bit)
                output.append(byte_value)

        commands.append(bytes(output))

    return commands


def _split_image(image: Image.Image, max_height: int = 255):
    """Split image into vertical chunks.

    Args:
        image: PIL Image to split
        max_height: Maximum height per chunk in pixels

    Yields:
        Image chunks
    """
    chunks = image.height // max_height

    for chunk in range(chunks + 1):
        y_start = chunk * max_height
        y_end = min(chunk * max_height + max_height, image.height)

        if y_start < image.height:
            yield image.crop((0, y_start, image.width, y_end))


def _image_to_bits(image: Image.Image, threshold: int = 127):
    """Convert image pixels to binary bits.

    Args:
        image: PIL Image in mode '1'
        threshold: Brightness threshold (0-255)

    Returns:
        List of bytearrays containing binary pixel data (one per line)
    """
    return [
        bytearray([
            1 if image.getpixel((x, y)) > threshold else 0
            for x in range(image.width)
        ])
        for y in range(image.height)
    ]
