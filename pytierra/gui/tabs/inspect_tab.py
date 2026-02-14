"""Inspect tab — genotype details and full genome disassembly."""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from pytierra.controller import GenotypeSnapshot
from pytierra.genome_io import OPCODE_TO_NAME

from . import render_genome_bar


class InspectTab(QWidget):
    """Shows genotype-level info with full genome disassembly."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._genotype: Optional[GenotypeSnapshot] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header
        self._header = QLabel("No genotype selected")
        self._header.setWordWrap(True)
        self._header.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self._header)

        # Genome bar
        self._genome_bar = QLabel()
        self._genome_bar.setFixedHeight(24)
        self._genome_bar.setScaledContents(True)
        self._genome_bar.setToolTip("Genome visualization: each pixel is one instruction, colored by opcode")
        layout.addWidget(self._genome_bar)

        # Full disassembly
        self._disasm_text = QPlainTextEdit()
        self._disasm_text.setReadOnly(True)
        self._disasm_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = self._disasm_text.font()
        font.setFamily("monospace")
        font.setPointSize(10)
        self._disasm_text.setFont(font)
        layout.addWidget(self._disasm_text, stretch=1)

        # Copy button
        self._copy_btn = QPushButton("Copy Disassembly")
        self._copy_btn.setToolTip("Copy the full disassembly text to clipboard")
        self._copy_btn.clicked.connect(self._copy_to_clipboard)
        layout.addWidget(self._copy_btn)

    def set_genotype(self, genotype: Optional[GenotypeSnapshot]) -> None:
        """Set the genotype to display."""
        self._genotype = genotype
        if genotype is None:
            self._header.setText("No genotype selected")
            self._genome_bar.clear()
            self._disasm_text.clear()
            return

        # Header
        self._header.setText(
            f"Name: {genotype.name}  Parent: {genotype.parent}\n"
            f"Origin: {genotype.origin_time}  "
            f"Pop: {genotype.population}  Max: {genotype.max_pop}"
        )

        # Genome bar
        img = render_genome_bar(genotype.genome, height=24)
        self._genome_bar.setPixmap(QPixmap.fromImage(img))

        # Full disassembly
        lines = []
        for i, opcode in enumerate(genotype.genome):
            mnemonic = OPCODE_TO_NAME.get(opcode % 32, f"?{opcode}")
            lines.append(f"{i:3d}  {opcode:02x}  {mnemonic}")
        self._disasm_text.setPlainText("\n".join(lines))

    def _copy_to_clipboard(self) -> None:
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self._disasm_text.toPlainText())
