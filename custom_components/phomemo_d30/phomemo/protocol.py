"""Phomemo D30 protocol encoding.

This module handles image preprocessing and protocol encoding for the Phomemo D30 printer.
Adapted from phomemo-tools by Laurent Vivier (https://github.com/vivier/phomemo-tools).

Licensed under GPL-3.0, compatible with the project's GPL-3.0 license.
"""

from io import BytesIO
from PIL import Image


def preprocess_image(image: Image.Image, target_width: int = 384) -> Image.Image:
    """Preprocess image for D30 printer.

    The D30 printer expects:
    - Auto-rotate if landscape (width > height)
    - Resize to target width (384 dots for D30) maintaining aspect ratio
    - Convert to 1-bit black/white using dithering

    Args:
        image: Input PIL Image in any mode (RGB, RGBA, L, etc.)
        target_width: Target width in dots (default: 384 for D30)

    Returns:
        Preprocessed PIL Image in mode '1' (1-bit black/white)
    """
    # Auto-rotate if landscape orientation
    if image.width > image.height:
        image = image.transpose(Image.Transpose.ROTATE_90)

    # Resize to target width while maintaining aspect ratio
    if image.width != target_width:
        aspect_ratio = image.height / image.width
        new_height = int(target_width * aspect_ratio)
        image = image.resize((target_width, new_height), Image.Resampling.LANCZOS)

    # Convert to 1-bit black/white using dithering
    # This automatically handles grayscale conversion and dithering
    image = image.convert(mode='1')

    return image


def encode_print_command(image: Image.Image) -> bytes:
    """Encode a complete print command for the D30 printer.

    This function creates the complete byte sequence to send to the printer,
    using the proprietary Phomemo protocol discovered by packet sniffing.

    Args:
        image: PIL Image in mode '1' (1-bit black/white)

    Returns:
        Complete byte sequence ready to send to printer

    Raises:
        ValueError: If image is not in mode '1'
    """
    if image.mode != '1':
        raise ValueError(f"Image must be in mode '1' (1-bit), got '{image.mode}'")

    output = BytesIO()

    # 1. Print header
    output.write(b'\x1b\x40\x1b\x61\x01\x1f\x11\x02\x04')

    # 2. Print image data
    # Process image in chunks of up to 256 lines
    lines_remaining = image.height
    line_offset = 0

    while lines_remaining > 0:
        # Determine chunk size (max 256 lines)
        chunk_lines = min(lines_remaining, 256)

        # Write marker for this chunk
        output.write(_encode_marker(chunk_lines))

        # Write each line in the chunk
        for line_num in range(chunk_lines):
            output.write(_encode_line(image, line_offset + line_num))

        line_offset += chunk_lines
        lines_remaining -= chunk_lines

    # 3. Print footer
    output.write(b'\x1b\x64\x02')  # Feed 2 lines
    output.write(b'\x1b\x64\x02')  # Feed 2 lines (again)
    output.write(b'\x1f\x11\x08')  # Unknown control sequence
    output.write(b'\x1f\x11\x0e')  # Unknown control sequence
    output.write(b'\x1f\x11\x07')  # Unknown control sequence
    output.write(b'\x1f\x11\x09')  # Unknown control sequence

    return output.getvalue()


def _encode_marker(lines: int) -> bytes:
    """Encode marker block for a chunk of lines.

    Args:
        lines: Number of lines in this chunk (1-256)

    Returns:
        Marker byte sequence
    """
    output = BytesIO()

    # Magic marker value
    output.write((0x761d).to_bytes(2, 'little'))

    # Two 0x0030 values (unknown purpose)
    output.write((0x0030).to_bytes(2, 'little'))
    output.write((0x0030).to_bytes(2, 'little'))

    # Number of lines minus 1 (little-endian)
    output.write((lines - 1).to_bytes(2, 'little'))

    return output.getvalue()


def _encode_line(image: Image.Image, line: int) -> bytes:
    """Encode a single line of the image.

    Converts pixels to packed bits, with special handling for 0x0a bytes
    to prevent the printer from interpreting them as line feeds.

    Args:
        image: PIL Image in mode '1'
        line: Line number to encode (0-based)

    Returns:
        Encoded line bytes
    """
    output = BytesIO()

    # Calculate bytes per line (width / 8, rounded up)
    bytes_per_line = (image.width + 7) // 8

    # Get pixel data for this line
    for byte_num in range(bytes_per_line):
        byte_value = 0

        # Pack 8 pixels into one byte
        for bit in range(8):
            pixel_x = byte_num * 8 + bit

            if pixel_x < image.width:
                # Get pixel value (0 = black, 255 = white in mode '1')
                pixel = image.getpixel((pixel_x, line))

                # Set bit to 1 if pixel is black (0)
                if pixel == 0:
                    byte_value |= (1 << (7 - bit))

        # CRITICAL: Replace 0x0a with 0x14 to prevent line feed interpretation
        # The printer interprets 0x0a (LF) as a control character
        if byte_value == 0x0a:
            byte_value = 0x14

        output.write(byte_value.to_bytes(1, 'little'))

    return output.getvalue()
