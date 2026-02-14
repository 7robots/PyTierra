"""Selection settings tab — slice size, lazy tolerance controls."""

from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QGroupBox, QHBoxLayout, QLabel,
    QSpinBox, QVBoxLayout, QWidget,
)

from pytierra.controller import SimulationController


class SelectionTab(QWidget):
    """Settings panel for time-slicing and selection pressure."""

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

        # --- Slice Size ---
        slice_group = QGroupBox("Time Slice")
        slice_layout = QVBoxLayout(slice_group)

        # Fixed slice size
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(QLabel("Base slice size:"))
        self._slice_size = QSpinBox()
        self._slice_size.setRange(1, 1000)
        self._slice_size.setValue(25)
        self._slice_size.setToolTip("Number of instructions per time slice (when not size-dependent)")
        self._slice_size.valueChanged.connect(
            lambda v: self._on_changed("slice_size", v)
        )
        row_layout.addWidget(self._slice_size)
        slice_layout.addWidget(row)

        # Size-dependent toggle
        self._siz_dep_check = QCheckBox("Size-dependent slicing")
        self._siz_dep_check.setToolTip(
            "When enabled, slice size = cell_size ^ slice_pow"
        )
        self._siz_dep_check.toggled.connect(self._on_siz_dep_toggled)
        slice_layout.addWidget(self._siz_dep_check)

        # Slice power
        row2 = QWidget()
        row2_layout = QHBoxLayout(row2)
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.addWidget(QLabel("Slice power:"))
        self._slice_pow = QDoubleSpinBox()
        self._slice_pow.setRange(0.1, 3.0)
        self._slice_pow.setValue(1.0)
        self._slice_pow.setSingleStep(0.1)
        self._slice_pow.setToolTip("Exponent for size-dependent slicing")
        self._slice_pow.valueChanged.connect(
            lambda v: self._on_changed("slice_pow", v)
        )
        row2_layout.addWidget(self._slice_pow)
        slice_layout.addWidget(row2)

        layout.addWidget(slice_group)

        # --- Random Variation ---
        var_group = QGroupBox("Slice Variation (Style 2)")
        var_layout = QVBoxLayout(var_group)

        row3 = QWidget()
        row3_layout = QHBoxLayout(row3)
        row3_layout.setContentsMargins(0, 0, 0, 0)
        row3_layout.addWidget(QLabel("Fixed fraction:"))
        self._slic_fix_frac = QDoubleSpinBox()
        self._slic_fix_frac.setRange(0.0, 10.0)
        self._slic_fix_frac.setValue(0.0)
        self._slic_fix_frac.setSingleStep(0.1)
        self._slic_fix_frac.setToolTip("Multiplier for fixed part of slice")
        self._slic_fix_frac.valueChanged.connect(
            lambda v: self._on_changed("slic_fix_frac", v)
        )
        row3_layout.addWidget(self._slic_fix_frac)
        var_layout.addWidget(row3)

        row4 = QWidget()
        row4_layout = QHBoxLayout(row4)
        row4_layout.setContentsMargins(0, 0, 0, 0)
        row4_layout.addWidget(QLabel("Random fraction:"))
        self._slic_ran_frac = QDoubleSpinBox()
        self._slic_ran_frac.setRange(0.0, 10.0)
        self._slic_ran_frac.setValue(2.0)
        self._slic_ran_frac.setSingleStep(0.1)
        self._slic_ran_frac.setToolTip("Multiplier for random part of slice")
        self._slic_ran_frac.valueChanged.connect(
            lambda v: self._on_changed("slic_ran_frac", v)
        )
        row4_layout.addWidget(self._slic_ran_frac)
        var_layout.addWidget(row4)

        layout.addWidget(var_group)

        # --- Lazy Tolerance ---
        lazy_group = QGroupBox("Lazy Tolerance")
        lazy_layout = QVBoxLayout(lazy_group)

        row5 = QWidget()
        row5_layout = QHBoxLayout(row5)
        row5_layout.setContentsMargins(0, 0, 0, 0)
        row5_layout.addWidget(QLabel("Lazy tolerance:"))
        self._lazy_tol = QSpinBox()
        self._lazy_tol.setRange(0, 100)
        self._lazy_tol.setValue(10)
        self._lazy_tol.setToolTip(
            "Kill cell if instructions > size * lazy_tol without reproducing. 0 = disabled."
        )
        self._lazy_tol.valueChanged.connect(
            lambda v: self._on_changed("lazy_tol", v)
        )
        row5_layout.addWidget(self._lazy_tol)
        lazy_layout.addWidget(row5)

        layout.addWidget(lazy_group)

        layout.addStretch()

    def _on_siz_dep_toggled(self, checked: bool) -> None:
        self._on_changed("siz_dep_slice", 1 if checked else 0)
        self._slice_pow.setEnabled(checked)

    def _on_changed(self, key: str, value) -> None:
        if self._controller is not None:
            self._controller.update_config(**{key: value})

    def _load_from_config(self) -> None:
        if self._controller is None or self._controller.simulation is None:
            return
        cfg = self._controller.simulation.config
        self._slice_size.setValue(cfg.slice_size)
        self._siz_dep_check.setChecked(bool(cfg.siz_dep_slice))
        self._slice_pow.setValue(cfg.slice_pow)
        self._slice_pow.setEnabled(bool(cfg.siz_dep_slice))
        self._slic_fix_frac.setValue(cfg.slic_fix_frac)
        self._slic_ran_frac.setValue(cfg.slic_ran_frac)
        self._lazy_tol.setValue(cfg.lazy_tol)
