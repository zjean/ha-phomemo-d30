"""Phomemo D30 protocol encoding.

This module handles image preprocessing and protocol encoding for the Phomemo D30 printer.
Adapted from phomemo-tools by Laurent Vivier (https://github.com/vivier/phomemo-tools).

Licensed under GPL-3.0, compatible with the project's GPL-3.0 license.
"""

from io import BytesIO
from PIL import Image, ImageOps

# Protocol control characters
ESC = b'\x1b'
GS = b'\x1d'


def preprocess_image(image: Image.Image) -> Image.Image:
    """Preprocess image for D30 printer.

    The D30 printer expects:
    - 1-bit black/white image (mode '1')
    - Image rotated 90 degrees clockwise
    - Inverted colors (white becomes black, black becomes white)

    Args:
        image: Input PIL Image in any mode (RGB, RGBA, L, etc.)

    Returns:
        Preprocessed PIL Image in mode '1' (1-bit black/white), rotated 90 degrees
    """
    # Convert to grayscale first if needed
    if image.mode != 'L':
        image = image.convert('L')

    # Invert the image (D30 expects inverted)
    image = ImageOps.invert(image)

    # Convert to 1-bit black/white
    image = image.convert('1')

    # Rotate 90 degrees clockwise (transpose)
    image = image.transpose(Image.ROTATE_90)

    return image


def bytes_per_line(image: Image.Image) -> int:
    """Calculate bytes per line for image data.

    Args:
        image: PIL Image

    Returns:
        Number of bytes needed per line (width / 8, rounded up)
    """
    return int((image.width + 7) / 8)


def encode_print_command(image: Image.Image, feed_lines: int = 0) -> bytes:
    """Encode a complete print command for the D30 printer.

    This function creates the complete byte sequence to send to the printer,
    including initialization, print command header, image data, and optional
    paper feed.

    Args:
        image: PIL Image in mode '1' (1-bit black/white)
        feed_lines: Number of blank lines to feed after printing (default: 0)

    Returns:
        Complete byte sequence ready to send to printer

    Raises:
        ValueError: If image is not in mode '1'
    """
    if image.mode != '1':
        raise ValueError(f"Image must be in mode '1' (1-bit), got '{image.mode}'")

    output = BytesIO()

    # 1. Printer initialization
    # This sequence comes from sniffing USB traffic, purpose unclear but needed
    output.write(bytes.fromhex('1f112400'))

    # ESC @ - Initialize printer
    output.write(ESC + b'@')

    # 2. Start print command
    # GS v 0 - Print raster bit image
    output.write(GS + b'v0')

    # Mode: 0=normal, 1=double width, 2=double height, 3=quadruple
    mode = 0
    output.write(mode.to_bytes(1, 'little'))

    # Number of bytes per line (little-endian, 2 bytes)
    bpl = bytes_per_line(image)
    output.write(bpl.to_bytes(2, 'little'))

    # Image height in pixels (little-endian, 2 bytes)
    output.write(image.height.to_bytes(2, 'little'))

    # 3. Image data
    output.write(image.tobytes())

    # 4. Optional paper feed (blank lines)
    if feed_lines > 0:
        output.write(bytes(bpl * feed_lines))

    return output.getvalue()
