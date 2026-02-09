"""Phomemo D30 protocol encoding.

This module handles image preprocessing and protocol encoding for the Phomemo D30 printer.
Adapted from polskafan/phomemo_d30 (https://github.com/polskafan/phomemo_d30).

Licensed under GPL-3.0, compatible with the project's GPL-3.0 license.
"""

from io import BytesIO
import logging
import math
from PIL import Image, ImageOps

_LOGGER = logging.getLogger(__name__)


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
    _LOGGER.debug("=== IMAGE PREPROCESSING START ===")
    _LOGGER.debug("Input image size: %s", image.size)
    _LOGGER.debug("Input image mode: %s", image.mode)
    _LOGGER.debug("Target width: %d dots", target_width)

    # Resize to target width while maintaining aspect ratio
    src_w, src_h = image.size
    aspect = src_w / src_h
    new_size = (target_width, math.floor(target_width / aspect))

    _LOGGER.debug("Calculated new size: %s (aspect ratio: %.3f)", new_size, aspect)
    _LOGGER.debug("Resizing using LANCZOS resampling...")

    resized = image.resize(new_size, Image.Resampling.LANCZOS)
    _LOGGER.debug("Resized to: %s", resized.size)

    # Sample some pixels before inversion
    if resized.mode in ('RGB', 'RGBA', 'L'):
        try:
            sample_pixels = [resized.getpixel((x, 0)) for x in range(min(5, resized.width))]
            _LOGGER.debug("Sample pixels before inversion (first 5): %s", sample_pixels)
        except Exception as e:
            _LOGGER.debug("Could not sample pixels: %s", e)

    # Invert, convert to RGB, then to 1-bit (matching polskafan's implementation)
    _LOGGER.debug("Converting to RGB...")
    rgb_image = resized.convert("RGB")

    _LOGGER.debug("Inverting colors...")
    inverted = ImageOps.invert(rgb_image)

    _LOGGER.debug("Converting to 1-bit black/white...")
    converted = inverted.convert("1")

    # Sample some pixels after conversion
    try:
        sample_pixels_after = [converted.getpixel((x, 0)) for x in range(min(5, converted.width))]
        _LOGGER.debug("Sample pixels after conversion (first 5): %s", sample_pixels_after)
        _LOGGER.debug("Note: In mode '1', 0=black, 255=white")
    except Exception as e:
        _LOGGER.debug("Could not sample converted pixels: %s", e)

    _LOGGER.debug("Final image size: %s", converted.size)
    _LOGGER.debug("Final image mode: %s", converted.mode)
    _LOGGER.debug("=== IMAGE PREPROCESSING COMPLETE ===")

    return converted


def get_initialization_packets() -> list[bytes]:
    """Get initialization packets for D30 printer.

    These packets were sniffed from Android app "Print Master".
    Must be sent before each print command.

    Returns:
        List of initialization packet bytes
    """
    _LOGGER.debug("Getting D30 initialization packets")

    packet_descriptions = [
        ('1f1138', 'Init packet 1'),
        ('1f11121f1113', 'Init packet 2'),
        ('1f1109', 'Init packet 3'),
        ('1f1111', 'Init packet 4'),
        ('1f1119', 'Init packet 5'),
        ('1f1107', 'Init packet 6'),
        ('1f110a1f110202', 'Init packet 7'),
    ]

    packets = []
    for hex_str, description in packet_descriptions:
        packet = bytes.fromhex(hex_str)
        _LOGGER.debug("  %s: %s (%d bytes)", description, hex_str, len(packet))
        packets.append(packet)

    _LOGGER.debug("Total initialization packets: %d", len(packets))
    return packets


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
    _LOGGER.debug("=== ENCODE PRINT COMMAND START ===")
    _LOGGER.debug("Image size: %s", image.size)
    _LOGGER.debug("Image mode: %s", image.mode)
    _LOGGER.debug("Threshold: %d", threshold)

    if image.mode != '1':
        _LOGGER.error("❌ Invalid image mode: expected '1', got '%s'", image.mode)
        raise ValueError(f"Image must be in mode '1' (1-bit), got '{image.mode}'")

    width = image.width
    height = image.height
    _LOGGER.debug("Image dimensions: %dx%d", width, height)

    if width % 8 != 0:
        _LOGGER.warning("⚠️  Image width %d is not divisible by 8, may cause issues", width)

    commands = []
    chunk_count = 0

    # Split image into chunks of max 255 lines each
    _LOGGER.debug("Splitting image into chunks (max 255 lines each)...")

    for chunk in _split_image(image, max_height=255):
        chunk_count += 1
        chunk_height = chunk.height
        chunk_width = chunk.width

        _LOGGER.debug("Processing chunk %d: size=%s", chunk_count, chunk.size)

        # Build print command header dynamically based on chunk size
        # Format: 1f1124001b40 1d7630 00 WW_WW HH_HH
        # Where WW_WW = width in bytes (LSB, MSB), HH_HH = height in lines (LSB, MSB)
        width_bytes = chunk_width // 8

        output = bytearray()
        output.extend(bytes.fromhex('1f1124001b40'))  # Command prefix + ESC @
        output.extend(bytes.fromhex('1d763000'))      # GS v 0 0 (print raster bit image)
        output.append(width_bytes & 0xFF)             # Width LSB
        output.append((width_bytes >> 8) & 0xFF)      # Width MSB
        output.append(chunk_height & 0xFF)            # Height LSB
        output.append((chunk_height >> 8) & 0xFF)     # Height MSB

        _LOGGER.debug("  Header: prefix + dimensions (%d bytes)", len(output))
        _LOGGER.debug("  Width: %d bytes (%d dots), Height: %d lines",
                     width_bytes, chunk_width, chunk_height)

        # Convert chunk to bits
        _LOGGER.debug("  Converting chunk to bits (threshold=%d)...", threshold)
        bits = _image_to_bits(chunk, threshold)
        _LOGGER.debug("  Generated %d lines of bit data", len(bits))

        # Sample first line
        if bits:
            first_line_sample = bits[0][:min(8, len(bits[0]))]
            _LOGGER.debug("  First line sample (first 8 bits): %s", first_line_sample)

        # Encode each line
        bytes_per_line = width // 8
        _LOGGER.debug("  Encoding %d lines, %d bytes per line...", chunk_height, bytes_per_line)

        encoded_bytes = 0
        for line_num, line in enumerate(bits):
            for byte_num in range(bytes_per_line):
                byte_value = 0
                for bit in range(8):
                    pixel = line[byte_num * 8 + bit]
                    byte_value |= (pixel & 0x01) << (7 - bit)
                output.append(byte_value)
                encoded_bytes += 1

            # Log first few lines
            if line_num < 3:
                line_bytes = output[-bytes_per_line:]
                _LOGGER.debug("  Line %d bytes: %s%s",
                             line_num,
                             line_bytes[:4].hex(),
                             "..." if len(line_bytes) > 4 else "")

        _LOGGER.debug("  Chunk %d: encoded %d bytes of image data", chunk_count, encoded_bytes)
        _LOGGER.debug("  Total command size: %d bytes (header + data)", len(output))

        commands.append(bytes(output))

    _LOGGER.debug("Generated %d command(s) total", len(commands))
    total_bytes = sum(len(cmd) for cmd in commands)
    _LOGGER.debug("Total encoded data: %d bytes", total_bytes)
    _LOGGER.debug("=== ENCODE PRINT COMMAND COMPLETE ===")

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
    total_chunks = chunks + 1 if image.height % max_height != 0 else chunks

    _LOGGER.debug("Splitting %dx%d image into %d chunk(s) (max_height=%d)",
                 image.width, image.height, total_chunks, max_height)

    chunk_num = 0
    for chunk in range(chunks + 1):
        y_start = chunk * max_height
        y_end = min(chunk * max_height + max_height, image.height)

        if y_start < image.height:
            chunk_num += 1
            chunk_height = y_end - y_start
            _LOGGER.debug("  Chunk %d: rows %d-%d (height=%d)",
                         chunk_num, y_start, y_end, chunk_height)
            yield image.crop((0, y_start, image.width, y_end))


def _image_to_bits(image: Image.Image, threshold: int = 127):
    """Convert image pixels to binary bits.

    Args:
        image: PIL Image in mode '1'
        threshold: Brightness threshold (0-255)

    Returns:
        List of bytearrays containing binary pixel data (one per line)
    """
    _LOGGER.debug("  Converting %dx%d image to bits (threshold=%d)",
                 image.width, image.height, threshold)

    # Sample a few pixels to verify threshold behavior
    if image.height > 0 and image.width > 0:
        try:
            sample_count = min(5, image.width)
            samples = [(x, image.getpixel((x, 0))) for x in range(sample_count)]
            _LOGGER.debug("  Sample pixel values (x, value): %s", samples)
            _LOGGER.debug("  Threshold logic: pixel > %d → bit=1 (white), else bit=0 (black)", threshold)
        except Exception as e:
            _LOGGER.debug("  Could not sample pixels: %s", e)

    result = [
        bytearray([
            1 if image.getpixel((x, y)) > threshold else 0
            for x in range(image.width)
        ])
        for y in range(image.height)
    ]

    _LOGGER.debug("  Converted to %d lines of binary data", len(result))

    return result
