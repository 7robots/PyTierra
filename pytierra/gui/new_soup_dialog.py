"""New Soup configuration dialog."""

import random
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QGroupBox,
    QHBoxLayout, QLabel, QPushButton, QRadioButton,
    QSpinBox, QVBoxLayout,
)

from pytierra.config import Config
from pytierra.paths import default_ancestor_path


class NewSoupDialog(QDialog):
    """Dialog for configuring a new soup before simulation starts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Soup")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)

        # --- Soup Size ---
        size_group = QGroupBox("Soup Size")
        size_layout = QVBoxLayout(size_group)

        self._size_small = QRadioButton("Small (60,000)")
        self._size_medium = QRadioButton("Medium (600,000)")
        self._size_large = QRadioButton("Large (6,000,000)")
        self._size_custom_radio = QRadioButton("Custom:")
        self._size_small.setChecked(True)

        self._size_custom_spin = QSpinBox()
        self._size_custom_spin.setRange(1000, 100_000_000)
        self._size_custom_spin.setValue(60_000)
        self._size_custom_spin.setEnabled(False)

        self._size_custom_radio.toggled.connect(self._size_custom_spin.setEnabled)

        size_layout.addWidget(self._size_small)
        size_layout.addWidget(self._size_medium)
        size_layout.addWidget(self._size_large)
        custom_row = QHBoxLayout()
        custom_row.addWidget(self._size_custom_radio)
        custom_row.addWidget(self._size_custom_spin)
        custom_row.addStretch()
        size_layout.addLayout(custom_row)
        layout.addWidget(size_group)

        # --- Random Seed ---
        seed_group = QGroupBox("Random Seed")
        seed_layout = QHBoxLayout(seed_group)

        self._seed_spin = QSpinBox()
        self._seed_spin.setRange(0, 2_147_483_647)
        self._seed_spin.setValue(0)
        self._seed_spin.setSpecialValueText("0 (time-based)")

        random_btn = QPushButton("Random")
        random_btn.clicked.connect(
            lambda: self._seed_spin.setValue(random.randint(1, 2_147_483_647))
        )

        seed_layout.addWidget(QLabel("Seed:"))
        seed_layout.addWidget(self._seed_spin, 1)
        seed_layout.addWidget(random_btn)
        layout.addWidget(seed_group)

        # --- Ancestor ---
        ancestor_group = QGroupBox("Ancestor")
        ancestor_layout = QVBoxLayout(ancestor_group)

        self._ancestor_builtin = QRadioButton("Built-in (0080aaa)")
        self._ancestor_file_radio = QRadioButton("From file:")
        self._ancestor_builtin.setChecked(True)

        self._ancestor_path_label = QLabel("No file selected")
        self._ancestor_path_label.setEnabled(False)
        self._ancestor_browse_btn = QPushButton("Browse...")
        self._ancestor_browse_btn.setEnabled(False)
        self._ancestor_browse_btn.clicked.connect(self._browse_ancestor)

        self._ancestor_file_radio.toggled.connect(self._ancestor_path_label.setEnabled)
        self._ancestor_file_radio.toggled.connect(self._ancestor_browse_btn.setEnabled)

        ancestor_layout.addWidget(self._ancestor_builtin)
        ancestor_layout.addWidget(self._ancestor_file_radio)
        file_row = QHBoxLayout()
        file_row.addWidget(self._ancestor_path_label, 1)
        file_row.addWidget(self._ancestor_browse_btn)
        ancestor_layout.addLayout(file_row)
        layout.addWidget(ancestor_group)

        # --- Buttons ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._custom_ancestor_path: str = ""

    def _browse_ancestor(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Ancestor Genome", "", "Tierra Genome (*.tie);;All Files (*)"
        )
        if path:
            self._custom_ancestor_path = path
            self._ancestor_path_label.setText(Path(path).name)

    def get_config(self) -> Config:
        """Build a Config from dialog selections."""
        config = Config()

        if self._size_small.isChecked():
            config.soup_size = 60_000
        elif self._size_medium.isChecked():
            config.soup_size = 600_000
        elif self._size_large.isChecked():
            config.soup_size = 6_000_000
        else:
            config.soup_size = self._size_custom_spin.value()

        config.seed = self._seed_spin.value()
        return config

    def get_ancestor_path(self) -> str:
        """Return the path to the ancestor genome file."""
        if self._ancestor_builtin.isChecked():
            path = default_ancestor_path()
            return str(path) if path else ""
        return self._custom_ancestor_path
