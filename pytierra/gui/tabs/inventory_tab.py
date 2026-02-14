"""Inventory tab — sortable table of all living genotypes."""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHeaderView, QLineEdit, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from pytierra.controller import SimulationController


class InventoryTab(QWidget):
    """Sortable/filterable table of all living genotypes."""

    genotype_selected = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Filter
        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Filter genotypes...")
        self._filter.setToolTip("Type to filter genotypes by name")
        self._filter.textChanged.connect(self._apply_filter)
        layout.addWidget(self._filter)

        # Table
        self._table = QTableWidget(0, 5)
        self._table.setToolTip("Click a row to inspect that genotype")
        self._table.setHorizontalHeaderLabels(
            ["Name", "Size", "Population", "Max Pop", "Parent"]
        )
        self._table.setSortingEnabled(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._table.cellClicked.connect(self._on_cell_clicked)
        layout.addWidget(self._table)

    def refresh(self, controller: SimulationController) -> None:
        """Rebuild table from controller data."""
        genotypes = controller.get_all_genotypes()

        # Preserve sort state
        sort_col = self._table.horizontalHeader().sortIndicatorSection()
        sort_order = self._table.horizontalHeader().sortIndicatorOrder()

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(genotypes))

        for row, gt in enumerate(genotypes):
            name_item = QTableWidgetItem(gt.name)
            size_item = _NumericItem(len(gt.genome))
            pop_item = _NumericItem(gt.population)
            maxpop_item = _NumericItem(gt.max_pop)
            parent_item = QTableWidgetItem(gt.parent)

            self._table.setItem(row, 0, name_item)
            self._table.setItem(row, 1, size_item)
            self._table.setItem(row, 2, pop_item)
            self._table.setItem(row, 3, maxpop_item)
            self._table.setItem(row, 4, parent_item)

        self._table.setSortingEnabled(True)
        self._table.sortItems(sort_col, sort_order)
        self._apply_filter(self._filter.text())

    def _apply_filter(self, text: str) -> None:
        text = text.lower()
        for row in range(self._table.rowCount()):
            name_item = self._table.item(row, 0)
            if name_item is None:
                continue
            visible = text in name_item.text().lower()
            self._table.setRowHidden(row, not visible)

    def _on_cell_clicked(self, row: int, _col: int) -> None:
        name_item = self._table.item(row, 0)
        if name_item is not None:
            self.genotype_selected.emit(name_item.text())

    def clear(self) -> None:
        """Clear the table."""
        self._table.setRowCount(0)
        self._filter.clear()


class _NumericItem(QTableWidgetItem):
    """Table item that sorts numerically."""

    def __init__(self, value: int):
        super().__init__(str(value))
        self._value = value
        self.setTextAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

    def __lt__(self, other: QTableWidgetItem) -> bool:
        if isinstance(other, _NumericItem):
            return self._value < other._value
        return super().__lt__(other)
