"""Status bar widget with simulation metrics."""

from PySide6.QtWidgets import QLabel, QStatusBar


class StatusBarWidget(QStatusBar):
    """Status bar showing simulation metrics and hover info.

    Permanent widgets (right): Inst count, Cells, Fullness %, IPS
    Temporary message (left): Hover info (address, creature name, size)
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._inst_label = QLabel("Inst: 0")
        self._cells_label = QLabel("Cells: 0")
        self._fullness_label = QLabel("Full: 0.0%")
        self._ips_label = QLabel("IPS: 0")

        self.addPermanentWidget(self._inst_label)
        self.addPermanentWidget(self._cells_label)
        self.addPermanentWidget(self._fullness_label)
        self.addPermanentWidget(self._ips_label)

    def update_metrics(self, inst: int, cells: int, fullness: float, ips: float) -> None:
        self._inst_label.setText(f"Inst: {inst:,}")
        self._cells_label.setText(f"Cells: {cells}")
        self._fullness_label.setText(f"Full: {fullness:.1f}%")
        self._ips_label.setText(f"IPS: {ips:,.0f}")

    def show_hover_info(self, address: int, genotype: str = "", size: int = 0) -> None:
        if genotype:
            self.showMessage(f"Addr: {address:,}  |  {genotype}  (size {size})")
        else:
            self.showMessage(f"Addr: {address:,}  |  (free)")
