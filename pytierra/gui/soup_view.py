"""SoupView widget — renders the Tierra soup as a colored grid."""

import numpy as np
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QImage, QPainter, QWheelEvent, QMouseEvent
from PySide6.QtWidgets import QWidget


class SoupView(QWidget):
    """Widget that displays the soup memory as a 2D colored image.

    Each pixel represents one memory address, colored by opcode.
    Supports zoom, pan, and mouse hover/click interaction.
    """

    address_hovered = Signal(int)   # emitted on mouse move with soup address
    cell_selected = Signal(int)     # emitted on click with soup address

    MIN_ZOOM = 0.125
    MAX_ZOOM = 8.0
    ZOOM_FACTOR = 1.15

    def __init__(self, parent=None):
        super().__init__(parent)
        self._image: QImage | None = None
        self._grid_width: int = 512
        self._soup_size: int = 0
        self._zoom: float = 1.0

        # Overlay flags
        self._show_cells = False
        self._show_ips = False
        self._show_fecundity = False

        # Cell data for overlays (set externally before paint)
        self._cell_overlays: list[tuple[int, int, int, str]] = []  # (pos, size, ip, genotype)

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    @property
    def grid_width(self) -> int:
        return self._grid_width

    @grid_width.setter
    def grid_width(self, value: int) -> None:
        self._grid_width = max(1, value)

    def set_overlays(self, show_cells: bool, show_ips: bool, show_fecundity: bool) -> None:
        self._show_cells = show_cells
        self._show_ips = show_ips
        self._show_fecundity = show_fecundity

    def set_cell_data(self, cells: list[tuple[int, int, int, str]]) -> None:
        """Set cell overlay data: list of (pos, size, ip, genotype)."""
        self._cell_overlays = cells

    def update_image(self, rgba: np.ndarray, soup_size: int) -> None:
        """Update the displayed image from an RGBA numpy array (H, W, 4)."""
        self._soup_size = soup_size
        h, w = rgba.shape[:2]
        self._grid_width = w

        # Apply overlays in-place on a copy
        display = rgba.copy()
        if self._show_cells or self._show_ips or self._show_fecundity:
            self._apply_overlays(display)

        # Convert numpy RGBA to QImage (deep copy to decouple from numpy)
        self._image = QImage(
            display.data, w, h, w * 4, QImage.Format.Format_RGBA8888
        ).copy()

        # Resize widget to match zoomed image
        self.setMinimumSize(
            int(w * self._zoom), int(h * self._zoom)
        )
        self.update()

    def _apply_overlays(self, rgba: np.ndarray) -> None:
        """Apply visual overlays to the RGBA array."""
        h, w = rgba.shape[:2]
        total = h * w

        for pos, size, ip, genotype in self._cell_overlays:
            if self._show_cells:
                # Color cell boundaries with genotype-based color
                hue = hash(genotype) & 0xFFFFFF
                r = ((hue >> 16) & 0xFF) // 2 + 64
                g = ((hue >> 8) & 0xFF) // 2 + 64
                b = (hue & 0xFF) // 2 + 64

                for addr in range(pos, pos + size):
                    idx = addr % total
                    # Semi-transparent blend
                    rgba[idx // w, idx % w, 0] = (rgba[idx // w, idx % w, 0] + r) // 2
                    rgba[idx // w, idx % w, 1] = (rgba[idx // w, idx % w, 1] + g) // 2
                    rgba[idx // w, idx % w, 2] = (rgba[idx // w, idx % w, 2] + b) // 2

            if self._show_fecundity:
                # Yellow-orange heat on occupied memory
                for addr in range(pos, pos + size):
                    idx = addr % total
                    row, col = idx // w, idx % w
                    rgba[row, col, 0] = min(255, rgba[row, col, 0] + 40)
                    rgba[row, col, 1] = min(255, rgba[row, col, 1] + 20)
                    rgba[row, col, 2] = max(0, rgba[row, col, 2] - 30)

            if self._show_ips:
                # Bright green pixel at IP
                idx = ip % total
                row, col = idx // w, idx % w
                rgba[row, col] = [0, 255, 0, 255]

    def zoom_to_fit(self) -> None:
        """Adjust zoom so the full image fits in the viewport."""
        if self._image is None:
            return
        parent = self.parentWidget()
        if parent is None:
            return
        vw = parent.width() - 20
        vh = parent.height() - 20
        iw = self._image.width()
        ih = self._image.height()
        if iw <= 0 or ih <= 0:
            return
        self._zoom = max(self.MIN_ZOOM, min(vw / iw, vh / ih, self.MAX_ZOOM))
        self.setMinimumSize(int(iw * self._zoom), int(ih * self._zoom))
        self.update()

    def set_zoom(self, zoom: float) -> None:
        self._zoom = max(self.MIN_ZOOM, min(zoom, self.MAX_ZOOM))
        if self._image is not None:
            self.setMinimumSize(
                int(self._image.width() * self._zoom),
                int(self._image.height() * self._zoom),
            )
        self.update()

    def paintEvent(self, event) -> None:
        if self._image is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        scaled_w = int(self._image.width() * self._zoom)
        scaled_h = int(self._image.height() * self._zoom)
        painter.drawImage(
            0, 0,
            self._image.scaled(scaled_w, scaled_h, Qt.AspectRatioMode.IgnoreAspectRatio,
                               Qt.TransformationMode.FastTransformation),
        )
        painter.end()

    def wheelEvent(self, event: QWheelEvent) -> None:
        degrees = event.angleDelta().y() / 8.0
        notches = degrees / 15.0
        new_zoom = self._zoom * (self.ZOOM_FACTOR ** notches)
        self.set_zoom(new_zoom)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        addr = self._pos_to_address(event.position().toPoint())
        if addr is not None:
            self.address_hovered.emit(addr)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            addr = self._pos_to_address(event.position().toPoint())
            if addr is not None:
                self.cell_selected.emit(addr)

    def _pos_to_address(self, pos: QPoint) -> int | None:
        """Convert widget pixel position to soup address."""
        if self._image is None or self._zoom <= 0:
            return None
        x = int(pos.x() / self._zoom)
        y = int(pos.y() / self._zoom)
        if x < 0 or y < 0 or x >= self._grid_width:
            return None
        addr = y * self._grid_width + x
        if addr < 0 or addr >= self._soup_size:
            return None
        return addr
