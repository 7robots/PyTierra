"""Graphs tab — real-time time-series plots and histograms."""

from typing import Optional

import numpy as np
import pyqtgraph as pg

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QVBoxLayout, QWidget,
)

from pytierra.controller import SimulationController

# Configure pyqtgraph defaults
pg.setConfigOptions(antialias=True, background="k", foreground="w")

# Display names and series keys for time-series graphs
_TIME_SERIES = [
    ("Population Size", "population_size"),
    ("Mean Creature Size", "mean_creature_size"),
    ("Max Fitness (Fecundity)", "max_fitness"),
    ("Genotype Count", "num_genotypes"),
    ("Soup Fullness (%)", "soup_fullness"),
    ("Instructions / Second", "instructions_per_second"),
]

# Display names for histogram views
_HISTOGRAMS = [
    "Size Histogram",
    "Genotype Frequency (Top 20)",
]


class GraphTab(QWidget):
    """Real-time graphs and histograms of evolutionary dynamics."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._last_series_len: int = 0
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Selector row
        selector_row = QWidget()
        selector_layout = QHBoxLayout(selector_row)
        selector_layout.setContentsMargins(0, 0, 0, 0)

        self._selector = QComboBox()
        self._selector.setToolTip("Select which graph or histogram to display")
        for label, _key in _TIME_SERIES:
            self._selector.addItem(label)
        for label in _HISTOGRAMS:
            self._selector.addItem(label)
        self._selector.currentIndexChanged.connect(self._on_selection_changed)
        selector_layout.addWidget(self._selector)

        layout.addWidget(selector_row)

        # Plot widget (used for both line plots and bar charts)
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)
        layout.addWidget(self._plot_widget, stretch=1)

        # Create the line plot item (reused for time-series)
        self._line = self._plot_widget.plot(pen=pg.mkPen("c", width=2))

        # Bar chart item (created on demand for histograms)
        self._bar_item: Optional[pg.BarGraphItem] = None

    def refresh(self, controller: SimulationController) -> None:
        """Update the currently displayed graph from controller data."""
        idx = self._selector.currentIndex()
        num_ts = len(_TIME_SERIES)

        if idx < num_ts:
            self._refresh_time_series(controller, idx)
        elif idx == num_ts:
            self._refresh_size_histogram(controller)
        elif idx == num_ts + 1:
            self._refresh_genotype_frequency(controller)

    def clear(self) -> None:
        """Clear all graph data."""
        self._line.setData([], [])
        self._remove_bar_item()
        self._last_series_len = 0

    def _on_selection_changed(self, _idx: int) -> None:
        # Clear previous data and reset axis labels
        self._line.setData([], [])
        self._remove_bar_item()
        self._plot_widget.setLabel("bottom", "")
        self._plot_widget.setLabel("left", "")
        self._last_series_len = 0
        # Reset x-axis to linear (in case it was set to category for histograms)
        axis = self._plot_widget.getAxis("bottom")
        axis.setTicks(None)

    def _refresh_time_series(self, controller: SimulationController, idx: int) -> None:
        label, key = _TIME_SERIES[idx]
        dc = controller.data_collector
        series = dc.all_series().get(key)
        if series is None or len(series) == 0:
            return

        # Skip update if data hasn't changed
        if len(series) == self._last_series_len:
            return
        self._last_series_len = len(series)

        self._remove_bar_item()

        times = np.array(series.times(), dtype=np.float64)
        values = np.array(series.values(), dtype=np.float64)

        self._line.setData(times, values)
        self._plot_widget.setLabel("bottom", "Instructions")
        self._plot_widget.setLabel("left", label)

    def _refresh_size_histogram(self, controller: SimulationController) -> None:
        dc = controller.data_collector
        hist = dc.size_histogram
        if not hist:
            return

        self._line.setData([], [])

        sizes = sorted(hist.keys())
        counts = [hist[s] for s in sizes]

        self._remove_bar_item()
        self._bar_item = pg.BarGraphItem(
            x=sizes, height=counts, width=0.8,
            brush=pg.mkBrush(80, 180, 220, 200),
        )
        self._plot_widget.addItem(self._bar_item)
        self._plot_widget.setLabel("bottom", "Genome Size")
        self._plot_widget.setLabel("left", "Count")
        # Reset tick formatting
        axis = self._plot_widget.getAxis("bottom")
        axis.setTicks(None)

    def _refresh_genotype_frequency(self, controller: SimulationController) -> None:
        dc = controller.data_collector
        freq = dc.genotype_frequency
        if not freq:
            return

        self._line.setData([], [])

        # Top 20 by population
        top = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)[:20]
        names = [name for name, _count in top]
        counts = [count for _name, count in top]
        xs = list(range(len(names)))

        self._remove_bar_item()
        self._bar_item = pg.BarGraphItem(
            x=xs, height=counts, width=0.6,
            brush=pg.mkBrush(220, 140, 60, 200),
        )
        self._plot_widget.addItem(self._bar_item)
        self._plot_widget.setLabel("bottom", "Genotype")
        self._plot_widget.setLabel("left", "Population")

        # Set genotype names as x-axis tick labels
        axis = self._plot_widget.getAxis("bottom")
        ticks = [list(zip(xs, names))]
        axis.setTicks(ticks)

    def _remove_bar_item(self) -> None:
        if self._bar_item is not None:
            self._plot_widget.removeItem(self._bar_item)
            self._bar_item = None
