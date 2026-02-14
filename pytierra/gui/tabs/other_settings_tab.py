"""Other settings tab — allocation, reaper, division constraints, misc."""

from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QGroupBox, QHBoxLayout,
    QLabel, QSpinBox, QVBoxLayout, QWidget,
)

from pytierra.controller import SimulationController


_MAL_MODES = {
    0: "First Fit",
    1: "Better Fit",
    2: "Random",
    3: "Near Mother",
    4: "Near BX",
}


class OtherSettingsTab(QWidget):
    """Settings panel for allocation, reaper, division, and misc."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._controller: Optional[SimulationController] = None
        self._setup_ui()

    def set_controller(self, controller: SimulationController) -> None:
        self._controller = controller
        self._load_from_config()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # --- Memory Allocation ---
        alloc_group = QGroupBox("Memory Allocation")
        alloc_layout = QVBoxLayout(alloc_group)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(QLabel("Allocation mode:"))
        self._mal_mode = QComboBox()
        for mode_id, name in _MAL_MODES.items():
            self._mal_mode.addItem(name, mode_id)
        self._mal_mode.currentIndexChanged.connect(self._on_mal_mode_changed)
        row_layout.addWidget(self._mal_mode)
        alloc_layout.addWidget(row)

        layout.addWidget(alloc_group)

        # --- Reaper ---
        reaper_group = QGroupBox("Reaper")
        reaper_layout = QVBoxLayout(reaper_group)

        self._reap_rnd_prop = self._add_double_row(
            reaper_layout, "Reap random proportion:", 0.0, 1.0, 0.3, 0.05,
            "reap_rnd_prop",
            tooltip="Fraction of queue (oldest end) to randomly select victim from."
        )

        self._mal_reap_tol_check = QCheckBox("Near-address reaping")
        self._mal_reap_tol_check.setToolTip(
            "When allocation fails, prefer reaping cells near the requested address."
        )
        self._mal_reap_tol_check.toggled.connect(
            lambda checked: self._on_changed("mal_reap_tol", 1 if checked else 0)
        )
        reaper_layout.addWidget(self._mal_reap_tol_check)

        self._mal_tol = self._add_int_row(
            reaper_layout, "Near-address tolerance:", 1, 100, 20,
            "mal_tol",
            tooltip="Max distance = mal_tol * avg_size for near-address reaping."
        )

        layout.addWidget(reaper_group)

        # --- Division Constraints ---
        div_group = QGroupBox("Division Constraints")
        div_layout = QVBoxLayout(div_group)

        self._div_same_siz = QCheckBox("Require same size")
        self._div_same_siz.setToolTip("Daughter must be same size as mother.")
        self._div_same_siz.toggled.connect(
            lambda checked: self._on_changed("div_same_siz", 1 if checked else 0)
        )
        div_layout.addWidget(self._div_same_siz)

        self._div_same_gen = QCheckBox("Require same genotype")
        self._div_same_gen.setToolTip("Daughter must have same genotype as mother.")
        self._div_same_gen.toggled.connect(
            lambda checked: self._on_changed("div_same_gen", 1 if checked else 0)
        )
        div_layout.addWidget(self._div_same_gen)

        self._mov_prop_thr_div = self._add_double_row(
            div_layout, "Copy threshold for divide:", 0.0, 1.0, 0.7, 0.05,
            "mov_prop_thr_div",
            tooltip="Proportion of genome that must be copied before division is allowed."
        )

        layout.addWidget(div_group)

        # --- Cell Constraints ---
        cell_group = QGroupBox("Cell Constraints")
        cell_layout = QVBoxLayout(cell_group)

        self._min_cell_size = self._add_int_row(
            cell_layout, "Min cell size:", 1, 200, 12,
            "min_cell_size"
        )

        self._search_limit = self._add_int_row(
            cell_layout, "Search limit multiplier:", 1, 50, 5,
            "search_limit",
            tooltip="Multiplier for template matching search range."
        )

        layout.addWidget(cell_group)

        # --- Disturbance ---
        dist_group = QGroupBox("Disturbance")
        dist_layout = QVBoxLayout(dist_group)

        self._dist_prop = self._add_double_row(
            dist_layout, "Kill proportion:", 0.0, 1.0, 0.2, 0.05,
            "dist_prop",
            tooltip="Proportion of population killed per disturbance event."
        )

        layout.addWidget(dist_group)

        layout.addStretch()

    def _add_int_row(
        self, parent_layout: QVBoxLayout, label: str,
        min_val: int, max_val: int, default: int,
        config_key: str, tooltip: str = "",
    ) -> QSpinBox:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel(label)
        if tooltip:
            lbl.setToolTip(tooltip)
        row_layout.addWidget(lbl)

        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setMaximumWidth(100)
        if tooltip:
            spin.setToolTip(tooltip)
        spin.valueChanged.connect(lambda v, k=config_key: self._on_changed(k, v))
        row_layout.addWidget(spin)

        parent_layout.addWidget(row)
        return spin

    def _add_double_row(
        self, parent_layout: QVBoxLayout, label: str,
        min_val: float, max_val: float, default: float, step: float,
        config_key: str, tooltip: str = "",
    ) -> QDoubleSpinBox:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel(label)
        if tooltip:
            lbl.setToolTip(tooltip)
        row_layout.addWidget(lbl)

        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setSingleStep(step)
        spin.setMaximumWidth(100)
        if tooltip:
            spin.setToolTip(tooltip)
        spin.valueChanged.connect(lambda v, k=config_key: self._on_changed(k, v))
        row_layout.addWidget(spin)

        parent_layout.addWidget(row)
        return spin

    def _on_mal_mode_changed(self, index: int) -> None:
        mode_id = self._mal_mode.itemData(index)
        if mode_id is not None:
            self._on_changed("mal_mode", mode_id)

    def _on_changed(self, key: str, value) -> None:
        if self._controller is not None:
            self._controller.update_config(**{key: value})

    def _load_from_config(self) -> None:
        if self._controller is None or self._controller.simulation is None:
            return
        cfg = self._controller.simulation.config

        # Allocation
        idx = self._mal_mode.findData(cfg.mal_mode)
        if idx >= 0:
            self._mal_mode.setCurrentIndex(idx)

        # Reaper
        self._reap_rnd_prop.setValue(cfg.reap_rnd_prop)
        self._mal_reap_tol_check.setChecked(bool(cfg.mal_reap_tol))
        self._mal_tol.setValue(cfg.mal_tol)

        # Division
        self._div_same_siz.setChecked(bool(cfg.div_same_siz))
        self._div_same_gen.setChecked(bool(cfg.div_same_gen))
        self._mov_prop_thr_div.setValue(cfg.mov_prop_thr_div)

        # Cell
        self._min_cell_size.setValue(cfg.min_cell_size)
        self._search_limit.setValue(cfg.search_limit)

        # Disturbance
        self._dist_prop.setValue(cfg.dist_prop)
