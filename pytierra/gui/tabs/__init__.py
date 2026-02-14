"""Tabbed inspector panels for the PyTierra GUI."""

from PySide6.QtGui import QImage

import numpy as np

from pytierra.controller import _OPCODE_COLORS


def render_genome_bar(genome: bytes, height: int = 20) -> QImage:
    """Render genome as horizontal colored bar using opcode colors.

    Width = len(genome), each column is one instruction colored by opcode.
    """
    width = len(genome)
    if width == 0:
        return QImage(1, height, QImage.Format.Format_RGB32)

    opcodes = np.frombuffer(genome, dtype=np.uint8) % 32
    colors = _OPCODE_COLORS[opcodes]  # shape (width, 3)

    # Build RGBA image data
    img = QImage(width, height, QImage.Format.Format_RGB32)
    for x in range(width):
        r, g, b = int(colors[x, 0]), int(colors[x, 1]), int(colors[x, 2])
        color = (255 << 24) | (r << 16) | (g << 8) | b
        for y in range(height):
            img.setPixel(x, y, color)

    return img
