"""Mutation settings tab — controls for all mutation rate parameters."""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDoubleSpinBox, QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QVBoxLayout, QWidget,
)

from pytierra.controller import SimulationController


# Preset values: (gen_per_bkg_mut, gen_per_flaw, gen_per_div_mut)
_PRESETS = {
    "None": (0, 0, 0),
    "Low": (128, 128, 128),
    "Med": (32, 32, 32),
    "High": (8, 8, 8),
    "Very High": (2, 2, 2),
}


class MutationTab(QWidget):
    """Settings panel for mutation rates."""

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

        # --- Cosmic Ray (Background) Mutations ---
        cosmic_group = QGroupBox("Cosmic Ray (Background Mutation)")
        cosmic_layout = QVBoxLayout(cosmic_group)

        self._gen_per_bkg_mut = self._add_spin_row(
            cosmic_layout, "Generations per mutation:", 0, 1000, 32,
            "gen_per_bkg_mut",
            tooltip="0 = disabled. Lower = more frequent mutations."
        )
        self._rate_mut_label = QLabel("Rate: --")
        self._rate_mut_label.setStyleSheet("font-size: 10px; color: #888;")
        cosmic_layout.addWidget(self._rate_mut_label)
        layout.addWidget(cosmic_group)

        # --- Copy Error (Division Mutation) ---
        copy_group = QGroupBox("Copy Error (Division Mutation)")
        copy_layout = QVBoxLayout(copy_group)

        self._gen_per_div_mut = self._add_spin_row(
            copy_layout, "Generations per mutation:", 0, 1000, 32,
            "gen_per_div_mut",
            tooltip="0 = disabled. Applied at cell division."
        )
        layout.addWidget(copy_group)

        # --- Execution Flaw ---
        flaw_group = QGroupBox("Execution Flaw")
        flaw_layout = QVBoxLayout(flaw_group)

        self._gen_per_flaw = self._add_spin_row(
            flaw_layout, "Generations per flaw:", 0, 1000, 32,
            "gen_per_flaw",
            tooltip="0 = disabled. Random instruction errors during execution."
        )
        self._rate_flaw_label = QLabel("Rate: --")
        self._rate_flaw_label.setStyleSheet("font-size: 10px; color: #888;")
        flaw_layout.addWidget(self._rate_flaw_label)
        layout.addWidget(flaw_group)

        # --- Bit flip proportion ---
        bitflip_group = QGroupBox("Mutation Type")
        bitflip_layout = QVBoxLayout(bitflip_group)

        self._mut_bit_prop = self._add_double_spin_row(
            bitflip_layout, "Bit-flip probability:", 0.0, 1.0, 0.2, 0.05,
            "mut_bit_prop",
            tooltip="Probability of bit-flip vs. random replacement when mutating."
        )
        layout.addWidget(bitflip_group)

        # --- Genetic Operators (Division-time) ---
        genetic_group = QGroupBox("Genetic Operators (at Division)")
        genetic_layout = QVBoxLayout(genetic_group)

        self._gen_per_cro_ins_sam_siz = self._add_spin_row(
            genetic_layout, "Crossover (same size):", 0, 1000, 32,
            "gen_per_cro_ins_sam_siz"
        )
        self._gen_per_cro_ins = self._add_spin_row(
            genetic_layout, "Crossover (size-changing):", 0, 1000, 32,
            "gen_per_cro_ins"
        )
        self._gen_per_ins_ins = self._add_spin_row(
            genetic_layout, "Instruction insertion:", 0, 1000, 32,
            "gen_per_ins_ins"
        )
        self._gen_per_del_ins = self._add_spin_row(
            genetic_layout, "Instruction deletion:", 0, 1000, 32,
            "gen_per_del_ins"
        )
        self._gen_per_cro_seg = self._add_spin_row(
            genetic_layout, "Segment crossover:", 0, 1000, 32,
            "gen_per_cro_seg"
        )
        self._gen_per_ins_seg = self._add_spin_row(
            genetic_layout, "Segment insertion:", 0, 1000, 32,
            "gen_per_ins_seg"
        )
        self._gen_per_del_seg = self._add_spin_row(
            genetic_layout, "Segment deletion:", 0, 1000, 32,
            "gen_per_del_seg"
        )
        layout.addWidget(genetic_group)

        # --- Preset buttons ---
        preset_row = QWidget()
        preset_layout = QHBoxLayout(preset_row)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        preset_layout.addWidget(QLabel("Presets:"))
        for name, values in _PRESETS.items():
            btn = QPushButton(name)
            btn.setMaximumWidth(80)
            btn.clicked.connect(lambda checked, v=values: self._apply_preset(v))
            preset_layout.addWidget(btn)
        preset_layout.addStretch()
        layout.addWidget(preset_row)

        layout.addStretch()

    def _add_spin_row(
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
        spin.valueChanged.connect(lambda v, k=config_key: self._on_value_changed(k, v))
        row_layout.addWidget(spin)

        parent_layout.addWidget(row)
        return spin

    def _add_double_spin_row(
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
        spin.valueChanged.connect(lambda v, k=config_key: self._on_value_changed(k, v))
        row_layout.addWidget(spin)

        parent_layout.addWidget(row)
        return spin

    def _on_value_changed(self, config_key: str, value) -> None:
        if self._controller is not None:
            self._controller.update_config(**{config_key: value})
        self._update_rate_labels()

    def _apply_preset(self, values: tuple[int, int, int]) -> None:
        bkg, flaw, div = values
        self._gen_per_bkg_mut.setValue(bkg)
        self._gen_per_flaw.setValue(flaw)
        self._gen_per_div_mut.setValue(div)

    def _load_from_config(self) -> None:
        if self._controller is None or self._controller.simulation is None:
            return
        cfg = self._controller.simulation.config
        self._gen_per_bkg_mut.setValue(cfg.gen_per_bkg_mut)
        self._gen_per_div_mut.setValue(cfg.gen_per_div_mut)
        self._gen_per_flaw.setValue(cfg.gen_per_flaw)
        self._mut_bit_prop.setValue(cfg.mut_bit_prop)
        self._gen_per_cro_ins_sam_siz.setValue(cfg.gen_per_cro_ins_sam_siz)
        self._gen_per_cro_ins.setValue(cfg.gen_per_cro_ins)
        self._gen_per_ins_ins.setValue(cfg.gen_per_ins_ins)
        self._gen_per_del_ins.setValue(cfg.gen_per_del_ins)
        self._gen_per_cro_seg.setValue(cfg.gen_per_cro_seg)
        self._gen_per_ins_seg.setValue(cfg.gen_per_ins_seg)
        self._gen_per_del_seg.setValue(cfg.gen_per_del_seg)
        self._update_rate_labels()

    def _update_rate_labels(self) -> None:
        if self._controller is None or self._controller.simulation is None:
            return
        cfg = self._controller.simulation.config
        if cfg.rate_mut > 0:
            self._rate_mut_label.setText(f"Rate: {cfg.rate_mut:.6f} per inst")
        else:
            self._rate_mut_label.setText("Rate: disabled")
        if cfg.rate_flaw > 0:
            self._rate_flaw_label.setText(f"Rate: {cfg.rate_flaw:.6f} per inst")
        else:
            self._rate_flaw_label.setText("Rate: disabled")
