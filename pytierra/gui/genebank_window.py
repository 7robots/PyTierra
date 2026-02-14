"""Genebank window — persistent SQLite database of saved genotypes."""

import sqlite3
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from pytierra.controller import GenotypeSnapshot, SimulationController
from pytierra.genome_io import save_genome

_DB_DIR = Path.home() / ".pytierra"
_DB_PATH = _DB_DIR / "genebank.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS genotypes (
    name TEXT PRIMARY KEY,
    size INTEGER NOT NULL,
    genome BLOB NOT NULL,
    origin_time INTEGER DEFAULT 0,
    parent TEXT DEFAULT '',
    max_pop INTEGER DEFAULT 0,
    first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
    last_seen TEXT DEFAULT CURRENT_TIMESTAMP
)
"""


def _ensure_db() -> sqlite3.Connection:
    """Open (or create) the genebank database."""
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute(_CREATE_TABLE)
    conn.commit()
    return conn


class GenebankWindow(QMainWindow):
    """Separate window for browsing and managing the persistent genebank."""

    inject_requested = Signal(str, bytes)  # name, genome

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Genebank")
        self.resize(700, 500)

        self._controller: Optional[SimulationController] = None
        self._conn = _ensure_db()
        self._setup_ui()
        self._refresh_table()

    def set_controller(self, controller: SimulationController) -> None:
        self._controller = controller

    # --- Auto-collection ---

    def auto_collect(self, controller: SimulationController) -> None:
        """Save genotypes that meet population thresholds.

        Called periodically from the main app's update loop.
        """
        if controller.simulation is None:
            return
        cfg = controller.simulation.config
        genotypes = controller.get_all_genotypes()
        if not genotypes:
            return

        total_pop = sum(gt.population for gt in genotypes)
        if total_pop == 0:
            return

        for gt in genotypes:
            # Check thresholds: population count and population proportion
            pop_frac = gt.population / total_pop
            meets_count = gt.population >= cfg.sav_min_num
            meets_pop = pop_frac >= cfg.sav_thr_pop
            if meets_count and meets_pop:
                self._save_genotype(gt)

    def _save_genotype(self, gt: GenotypeSnapshot) -> None:
        """Insert or update a genotype in the database."""
        self._conn.execute(
            """INSERT INTO genotypes (name, size, genome, origin_time, parent, max_pop)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
                   max_pop = MAX(max_pop, excluded.max_pop),
                   last_seen = CURRENT_TIMESTAMP
            """,
            (gt.name, len(gt.genome), gt.genome, gt.origin_time, gt.parent, gt.max_pop),
        )
        self._conn.commit()

    # --- UI ---

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Filter row
        filter_row = QWidget()
        filter_layout = QHBoxLayout(filter_row)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.addWidget(QLabel("Filter:"))
        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Search by name or parent...")
        self._filter.textChanged.connect(self._apply_filter)
        filter_layout.addWidget(self._filter)
        layout.addWidget(filter_row)

        # Table
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["Name", "Size", "Max Pop", "Origin", "Parent", "Last Seen"]
        )
        self._table.setSortingEnabled(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self._table)

        # Button row
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        self._inject_btn = QPushButton("Inject into Soup")
        self._inject_btn.setToolTip("Inject the selected genotype into the soup at a random position.")
        self._inject_btn.clicked.connect(self._on_inject)
        btn_layout.addWidget(self._inject_btn)

        self._export_btn = QPushButton("Export .tie")
        self._export_btn.setToolTip("Save the selected genotype to a .tie file.")
        self._export_btn.clicked.connect(self._on_export)
        btn_layout.addWidget(self._export_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setToolTip("Remove the selected genotype from the genebank.")
        self._delete_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(self._delete_btn)

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self._refresh_table)
        btn_layout.addWidget(self._refresh_btn)

        btn_layout.addStretch()

        # Status
        self._status_label = QLabel()
        btn_layout.addWidget(self._status_label)

        layout.addWidget(btn_row)

    def _refresh_table(self) -> None:
        rows = self._conn.execute(
            "SELECT name, size, max_pop, origin_time, parent, last_seen FROM genotypes ORDER BY name"
        ).fetchall()

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(rows))

        for i, (name, size, max_pop, origin_time, parent, last_seen) in enumerate(rows):
            self._table.setItem(i, 0, QTableWidgetItem(name))
            self._table.setItem(i, 1, _NumItem(size))
            self._table.setItem(i, 2, _NumItem(max_pop))
            self._table.setItem(i, 3, _NumItem(origin_time))
            self._table.setItem(i, 4, QTableWidgetItem(parent or ""))
            self._table.setItem(i, 5, QTableWidgetItem(last_seen or ""))

        self._table.setSortingEnabled(True)
        self._status_label.setText(f"{len(rows)} genotypes")
        self._apply_filter(self._filter.text())

    def _apply_filter(self, text: str) -> None:
        text = text.lower()
        for row in range(self._table.rowCount()):
            name_item = self._table.item(row, 0)
            parent_item = self._table.item(row, 4)
            name_match = name_item and text in name_item.text().lower()
            parent_match = parent_item and text in parent_item.text().lower()
            self._table.setRowHidden(row, not (name_match or parent_match))

    def _selected_name(self) -> Optional[str]:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self._table.item(rows[0].row(), 0)
        return item.text() if item else None

    def _get_genome(self, name: str) -> Optional[bytes]:
        row = self._conn.execute(
            "SELECT genome FROM genotypes WHERE name = ?", (name,)
        ).fetchone()
        return row[0] if row else None

    def _on_inject(self) -> None:
        name = self._selected_name()
        if name is None:
            return
        genome = self._get_genome(name)
        if genome is not None:
            self.inject_requested.emit(name, genome)

    def _on_export(self) -> None:
        name = self._selected_name()
        if name is None:
            return
        genome = self._get_genome(name)
        if genome is None:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Genotype", f"{name}.tie", "Tierra Genome (*.tie)"
        )
        if path:
            # Look up parent for the file header
            row = self._conn.execute(
                "SELECT parent FROM genotypes WHERE name = ?", (name,)
            ).fetchone()
            parent = row[0] if row else ""
            save_genome(path, genome, name=name, parent=parent)

    def _on_delete(self) -> None:
        name = self._selected_name()
        if name is None:
            return
        reply = QMessageBox.question(
            self, "Delete Genotype",
            f"Delete '{name}' from the genebank?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._conn.execute("DELETE FROM genotypes WHERE name = ?", (name,))
            self._conn.commit()
            self._refresh_table()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._refresh_table()

    def closeEvent(self, event) -> None:
        self._conn.close()
        super().closeEvent(event)


class _NumItem(QTableWidgetItem):
    """Table item that sorts numerically."""

    def __init__(self, value: int):
        super().__init__(str(value))
        self._value = value
        self.setTextAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

    def __lt__(self, other: QTableWidgetItem) -> bool:
        if isinstance(other, _NumItem):
            return self._value < other._value
        return super().__lt__(other)
