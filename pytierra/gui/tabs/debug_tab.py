"""Debug tab — selected creature's CPU state and disassembly."""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QHeaderView, QLabel,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from pytierra.controller import CellSnapshot, SimulationController
from pytierra.genome_io import OPCODE_TO_NAME

from . import render_genome_bar


class DebugTab(QWidget):
    """Shows the selected creature's execution context."""

    _DISASM_ROWS = 21
    _DISASM_HALF = 10

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._cell: Optional[CellSnapshot] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # --- Header labels ---
        self._header = QLabel("No creature selected")
        self._header.setWordWrap(True)
        self._header.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self._header)

        # --- Registers 2x4 grid ---
        reg_group = QWidget()
        reg_layout = QGridLayout(reg_group)
        reg_layout.setContentsMargins(0, 0, 0, 0)
        reg_layout.setSpacing(2)

        self._reg_labels: dict[str, QLabel] = {}
        reg_tips = {
            "ax": "AX: general-purpose / address register",
            "bx": "BX: general-purpose / source address",
            "cx": "CX: counter / size register",
            "dx": "DX: general-purpose / destination register",
        }
        regs = [("ax", 0, 0), ("bx", 0, 1), ("cx", 1, 0), ("dx", 1, 1)]
        for name, row, col in regs:
            lbl = QLabel(f"{name}: 0")
            lbl.setStyleSheet("font-family: monospace; font-size: 11px;")
            lbl.setToolTip(reg_tips[name])
            reg_layout.addWidget(lbl, row, col)
            self._reg_labels[name] = lbl
        layout.addWidget(reg_group)

        # --- Flags ---
        flags_row = QWidget()
        flags_layout = QHBoxLayout(flags_row)
        flags_layout.setContentsMargins(0, 0, 0, 0)
        flags_layout.setSpacing(6)

        self._flag_labels: dict[str, QLabel] = {}
        flag_tips = {
            "E": "Error flag: set when an operation fails",
            "S": "Sign flag: set when result is negative",
            "Z": "Zero flag: set when result is zero",
        }
        for flag_name in ("E", "S", "Z"):
            lbl = QLabel(flag_name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedWidth(28)
            lbl.setStyleSheet(
                "font-weight: bold; font-size: 11px; padding: 2px; "
                "background-color: #555; color: #aaa; border-radius: 3px;"
            )
            lbl.setToolTip(flag_tips[flag_name])
            flags_layout.addWidget(lbl)
            self._flag_labels[flag_name] = lbl

        flags_layout.addStretch()
        layout.addWidget(flags_row)

        # --- Stack ---
        self._stack_table = QTableWidget(10, 1)
        self._stack_table.setToolTip("CPU stack (10 deep), highlighted row is stack pointer")
        self._stack_table.setHorizontalHeaderLabels(["Value"])
        self._stack_table.verticalHeader().setVisible(True)
        self._stack_table.horizontalHeader().setStretchLastSection(True)
        self._stack_table.setMaximumHeight(160)
        self._stack_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._stack_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        layout.addWidget(QLabel("Stack:"))
        layout.addWidget(self._stack_table)

        # --- Disassembly ---
        self._disasm_table = QTableWidget(self._DISASM_ROWS, 3)
        self._disasm_table.setToolTip("Disassembly centered on instruction pointer (highlighted row)")
        self._disasm_table.setHorizontalHeaderLabels(["Addr", "Hex", "Mnemonic"])
        self._disasm_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self._disasm_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._disasm_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._disasm_table.verticalHeader().setVisible(False)
        layout.addWidget(QLabel("Disassembly:"))
        layout.addWidget(self._disasm_table, stretch=1)

        # --- Genome bar ---
        self._genome_bar = QLabel()
        self._genome_bar.setFixedHeight(20)
        self._genome_bar.setScaledContents(True)
        self._genome_bar.setToolTip("Genome visualization: each pixel is one instruction, colored by opcode")
        layout.addWidget(self._genome_bar)

    def set_cell(self, cell: Optional[CellSnapshot]) -> None:
        """Set the cell to display. Called when soup view selection changes."""
        self._cell = cell
        if cell is None:
            self._header.setText("No creature selected")
            self._clear_display()
            return
        self._update_header(cell)
        self._update_registers(cell)
        self._update_flags(cell)
        self._update_stack(cell)

    def refresh(self, controller: SimulationController) -> None:
        """Refresh disassembly and genome bar from controller. Called per UI tick."""
        cell = self._cell
        if cell is None:
            return

        # Re-fetch the cell to get updated state
        updated = controller.get_cell(cell.cell_id)
        if updated is None or not updated.alive:
            self._cell = None
            self._header.setText("Creature died")
            self._clear_display()
            return

        self._cell = updated
        self._update_header(updated)
        self._update_registers(updated)
        self._update_flags(updated)
        self._update_stack(updated)
        self._update_disassembly(updated, controller)
        self._update_genome_bar(updated, controller)

    def _update_header(self, cell: CellSnapshot) -> None:
        self._header.setText(
            f"Genotype: {cell.genotype}  Parent: {cell.parent_genotype}\n"
            f"Pos: {cell.pos}..{cell.pos + cell.size}  "
            f"Fecundity: {cell.fecundity}  "
            f"Inst: {cell.inst_executed}  Mut: {cell.mutations}"
        )

    def _update_registers(self, cell: CellSnapshot) -> None:
        for name in ("ax", "bx", "cx", "dx"):
            val = getattr(cell, name)
            self._reg_labels[name].setText(f"{name}: {val} (0x{val & 0xFFFF:04x})")

    def _update_flags(self, cell: CellSnapshot) -> None:
        flags = {"E": cell.flag_e, "S": cell.flag_s, "Z": cell.flag_z}
        for name, is_set in flags.items():
            lbl = self._flag_labels[name]
            if is_set:
                lbl.setStyleSheet(
                    "font-weight: bold; font-size: 11px; padding: 2px; "
                    "background-color: #c02020; color: white; border-radius: 3px;"
                )
            else:
                lbl.setStyleSheet(
                    "font-weight: bold; font-size: 11px; padding: 2px; "
                    "background-color: #555; color: #aaa; border-radius: 3px;"
                )

    def _update_stack(self, cell: CellSnapshot) -> None:
        for i in range(10):
            val = cell.stack[i] if i < len(cell.stack) else 0
            item = QTableWidgetItem(f"{val}")
            if i == cell.sp:
                item.setBackground(QColor(80, 80, 180))
                item.setForeground(QColor(255, 255, 255))
            self._stack_table.setItem(i, 0, item)

    def _update_disassembly(self, cell: CellSnapshot, controller: SimulationController) -> None:
        ip = cell.ip
        start_addr = ip - self._DISASM_HALF
        raw = controller.read_soup(start_addr, self._DISASM_ROWS)

        highlight_color = QColor(255, 255, 180)
        for i in range(self._DISASM_ROWS):
            addr = start_addr + i
            if i < len(raw):
                opcode = raw[i]
                mnemonic = OPCODE_TO_NAME.get(opcode % 32, f"?{opcode}")
                hex_str = f"{opcode:02x}"
            else:
                mnemonic = ""
                hex_str = ""

            addr_item = QTableWidgetItem(f"{addr}")
            hex_item = QTableWidgetItem(hex_str)
            mnem_item = QTableWidgetItem(mnemonic)

            for item in (addr_item, hex_item, mnem_item):
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            if addr == ip:
                for item in (addr_item, hex_item, mnem_item):
                    item.setBackground(highlight_color)

            self._disasm_table.setItem(i, 0, addr_item)
            self._disasm_table.setItem(i, 1, hex_item)
            self._disasm_table.setItem(i, 2, mnem_item)

    def _update_genome_bar(self, cell: CellSnapshot, controller: SimulationController) -> None:
        genome_bytes = controller.read_soup(cell.pos, cell.size)
        if genome_bytes:
            img = render_genome_bar(genome_bytes, height=20)
            self._genome_bar.setPixmap(QPixmap.fromImage(img))
        else:
            self._genome_bar.clear()

    def _clear_display(self) -> None:
        for lbl in self._reg_labels.values():
            lbl.setText(f"{lbl.text().split(':')[0]}: 0")
        for lbl in self._flag_labels.values():
            lbl.setStyleSheet(
                "font-weight: bold; font-size: 11px; padding: 2px; "
                "background-color: #555; color: #aaa; border-radius: 3px;"
            )
        self._stack_table.clearContents()
        self._disasm_table.clearContents()
        self._genome_bar.clear()
