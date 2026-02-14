"""Main application window and entry point for the PyTierra GUI."""

import csv
import sys
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal, QObject, QSettings
from PySide6.QtGui import QAction, QColor, QKeySequence, QPalette
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QLabel, QMainWindow, QMenu, QMessageBox,
    QScrollArea, QSlider, QSplitter, QTabWidget, QToolBar, QWidget,
    QHBoxLayout,
)

import pytierra
from pytierra.config import Config
from pytierra.controller import SimulationController
from pytierra.persistence import save_state, load_state
from pytierra.simulation import Simulation

from .genebank_window import GenebankWindow
from .help_window import HelpWindow
from .new_soup_dialog import NewSoupDialog
from .soup_view import SoupView
from .status_bar import StatusBarWidget
from .tabs.debug_tab import DebugTab
from .tabs.graph_tab import GraphTab
from .tabs.inspect_tab import InspectTab
from .tabs.inventory_tab import InventoryTab
from .tabs.mutation_tab import MutationTab
from .tabs.other_settings_tab import OtherSettingsTab
from .tabs.selection_tab import SelectionTab

_MAX_RECENT_FILES = 10
_SETTINGS_ORG = "7robots"
_SETTINGS_APP = "PyTierra"


class _TickBridge(QObject):
    """Bridge that converts a callback on the sim thread to a Qt signal."""
    tick_occurred = Signal()


class MainWindow(QMainWindow):
    """Main application window with soup visualization and playback controls."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyTierra")
        self.resize(1024, 720)

        self._controller = SimulationController()
        self._tick_bridge = _TickBridge()
        self._controller.on_tick(self._tick_bridge.tick_occurred.emit)
        self._tick_bridge.tick_occurred.connect(self._on_tick, Qt.ConnectionType.QueuedConnection)

        # IPS tracking
        self._last_ips_time: float = 0.0
        self._last_ips_inst: int = 0
        self._current_ips: float = 0.0

        # Genebank window (lazily shown)
        self._genebank_window: GenebankWindow | None = None

        # Help window (lazily shown)
        self._help_window: HelpWindow | None = None

        # Auto-collection counter (run every ~60 UI frames ~ 2 seconds)
        self._auto_collect_counter: int = 0

        # Current file path
        self._current_file: str | None = None

        self._setup_ui()
        self._setup_menus()
        self._setup_toolbar()

        # UI refresh timer (~30fps)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(33)
        self._refresh_timer.timeout.connect(self._update_ui)

        # Show new soup dialog on startup
        QTimer.singleShot(0, self._new_soup)

    def _setup_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # Left: soup view in scroll area
        self._soup_view = SoupView()
        scroll = QScrollArea()
        scroll.setWidget(self._soup_view)
        scroll.setWidgetResizable(False)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        splitter.addWidget(scroll)

        # Right: tabbed inspector panels
        self._tabs = QTabWidget()
        self._debug_tab = DebugTab()
        self._inspect_tab = InspectTab()
        self._inventory_tab = InventoryTab()
        self._graph_tab = GraphTab()
        self._mutation_tab = MutationTab()
        self._selection_tab = SelectionTab()
        self._other_settings_tab = OtherSettingsTab()
        self._tabs.addTab(self._debug_tab, "Debug")
        self._tabs.addTab(self._inspect_tab, "Inspect")
        self._tabs.addTab(self._inventory_tab, "Inventory")
        self._tabs.addTab(self._graph_tab, "Graphs")
        self._tabs.addTab(self._mutation_tab, "Mutations")
        self._tabs.addTab(self._selection_tab, "Selection")
        self._tabs.addTab(self._other_settings_tab, "Settings")
        splitter.addWidget(self._tabs)

        self._selected_addr: int | None = None

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

        # Status bar
        self._status_bar = StatusBarWidget(self)
        self.setStatusBar(self._status_bar)

        # Wire up soup view signals
        self._soup_view.address_hovered.connect(self._on_address_hovered)
        self._soup_view.cell_selected.connect(self._on_cell_selected)
        self._inventory_tab.genotype_selected.connect(self._on_genotype_selected)

    def _setup_menus(self) -> None:
        menubar = self.menuBar()

        # --- File menu ---
        file_menu = menubar.addMenu("&File")

        new_action = QAction("&New Soup...", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.setToolTip("Create a new simulation")
        new_action.triggered.connect(self._new_soup)
        file_menu.addAction(new_action)

        file_menu.addSeparator()

        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.setToolTip("Open a saved .pytierra session")
        open_action.triggered.connect(self._open_session)
        file_menu.addAction(open_action)

        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.setToolTip("Save the current session")
        save_action.triggered.connect(self._save_session)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.setToolTip("Save the current session to a new file")
        save_as_action.triggered.connect(self._save_session_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        # Recent Files submenu
        self._recent_menu = QMenu("Recent Files", self)
        file_menu.addMenu(self._recent_menu)
        self._update_recent_menu()

        file_menu.addSeparator()

        # Export submenu
        export_menu = QMenu("&Export", self)
        file_menu.addMenu(export_menu)

        export_png = QAction("Soup Image as &PNG...", self)
        export_png.setToolTip("Export the soup visualization as a PNG image")
        export_png.triggered.connect(self._export_png)
        export_menu.addAction(export_png)

        export_csv = QAction("Graph Data as &CSV...", self)
        export_csv.setToolTip("Export time-series graph data as CSV")
        export_csv.triggered.connect(self._export_csv)
        export_menu.addAction(export_csv)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # --- Simulation menu ---
        sim_menu = menubar.addMenu("&Simulation")

        self._play_pause_menu_action = QAction("&Play", self)
        self._play_pause_menu_action.setShortcut(QKeySequence(Qt.Key.Key_Space))
        self._play_pause_menu_action.setToolTip("Play or pause the simulation (Space)")
        self._play_pause_menu_action.triggered.connect(self._toggle_play_pause)
        sim_menu.addAction(self._play_pause_menu_action)

        step_menu_action = QAction("S&tep", self)
        step_menu_action.setShortcut(QKeySequence(Qt.Key.Key_Right))
        step_menu_action.setToolTip("Execute one time slice (Right arrow)")
        step_menu_action.triggered.connect(self._on_step)
        sim_menu.addAction(step_menu_action)

        sim_menu.addSeparator()

        speed_up_action = QAction("Speed &Up", self)
        speed_up_action.setShortcut(QKeySequence(Qt.Key.Key_BracketRight))
        speed_up_action.setToolTip("Increase simulation speed (])")
        speed_up_action.triggered.connect(self._speed_up)
        sim_menu.addAction(speed_up_action)

        speed_down_action = QAction("Speed &Down", self)
        speed_down_action.setShortcut(QKeySequence(Qt.Key.Key_BracketLeft))
        speed_down_action.setToolTip("Decrease simulation speed ([)")
        speed_down_action.triggered.connect(self._speed_down)
        sim_menu.addAction(speed_down_action)

        # --- View menu ---
        view_menu = menubar.addMenu("&View")

        self._show_cells_action = QAction("Show &Cells", self)
        self._show_cells_action.setCheckable(True)
        self._show_cells_action.setToolTip("Color cells by genotype")
        self._show_cells_action.toggled.connect(self._update_overlays)
        view_menu.addAction(self._show_cells_action)

        self._show_ips_action = QAction("Show &IPs", self)
        self._show_ips_action.setCheckable(True)
        self._show_ips_action.setToolTip("Show instruction pointer positions as green dots")
        self._show_ips_action.toggled.connect(self._update_overlays)
        view_menu.addAction(self._show_ips_action)

        self._show_fecundity_action = QAction("Show &Fecundity", self)
        self._show_fecundity_action.setCheckable(True)
        self._show_fecundity_action.setToolTip("Heat-map overlay for occupied memory")
        self._show_fecundity_action.toggled.connect(self._update_overlays)
        view_menu.addAction(self._show_fecundity_action)

        view_menu.addSeparator()

        zoom_in = QAction("Zoom &In", self)
        zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in.setToolTip("Zoom in on the soup view")
        zoom_in.triggered.connect(lambda: self._soup_view.set_zoom(self._soup_view._zoom * 1.5))
        view_menu.addAction(zoom_in)

        zoom_out = QAction("Zoom &Out", self)
        zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out.setToolTip("Zoom out of the soup view")
        zoom_out.triggered.connect(lambda: self._soup_view.set_zoom(self._soup_view._zoom / 1.5))
        view_menu.addAction(zoom_out)

        zoom_fit = QAction("Zoom to &Fit", self)
        zoom_fit.setShortcut(QKeySequence("Ctrl+0"))
        zoom_fit.setToolTip("Fit the entire soup in the view")
        zoom_fit.triggered.connect(self._soup_view.zoom_to_fit)
        view_menu.addAction(zoom_fit)

        # --- Window menu ---
        window_menu = menubar.addMenu("&Window")
        genebank_action = QAction("&Genebank", self)
        genebank_action.setShortcut(QKeySequence("Ctrl+G"))
        genebank_action.setToolTip("Open the genebank window")
        genebank_action.triggered.connect(self._show_genebank)
        window_menu.addAction(genebank_action)

        # --- Help menu ---
        help_menu = menubar.addMenu("&Help")

        help_action = QAction("PyTierra &Help", self)
        help_action.setShortcut(QKeySequence("F1"))
        help_action.setToolTip("Open the help window")
        help_action.triggered.connect(self._show_help)
        help_menu.addAction(help_action)

        help_menu.addSeparator()

        about_action = QAction("&About PyTierra", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar("Playback")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._play_action = QAction("Play", self)
        self._play_action.setCheckable(True)
        self._play_action.setToolTip("Start or pause the simulation (Space)")
        self._play_action.toggled.connect(self._on_play_toggled)
        toolbar.addAction(self._play_action)

        self._step_action = QAction("Step", self)
        self._step_action.setToolTip("Execute one time slice (Right arrow)")
        self._step_action.triggered.connect(self._on_step)
        toolbar.addAction(self._step_action)

        toolbar.addSeparator()

        # Speed slider (log scale: 0-100 -> 1-10K slices/tick)
        speed_label = QLabel(" Speed: ")
        speed_label.setToolTip("Simulation speed: slices executed per tick")
        toolbar.addWidget(speed_label)
        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(0, 100)
        self._speed_slider.setValue(50)
        self._speed_slider.setMaximumWidth(200)
        self._speed_slider.setToolTip("Drag to adjust simulation speed ([ and ] keys also work)")
        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        toolbar.addWidget(self._speed_slider)

        self._speed_label = QLabel()
        self._speed_label.setToolTip("Current speed in slices per tick")
        toolbar.addWidget(self._speed_label)

        # Apply initial speed
        self._on_speed_changed(50)

    # --- Soup lifecycle ---

    def _new_soup(self) -> None:
        """Show the New Soup dialog and create a simulation."""
        was_running = self._controller.is_running
        if was_running:
            self._controller.pause()
            self._play_action.setChecked(False)

        dialog = NewSoupDialog(self)
        if dialog.exec() != NewSoupDialog.DialogCode.Accepted:
            return

        config = dialog.get_config()
        ancestor_path = dialog.get_ancestor_path()

        sim = Simulation(config=config)
        sim.boot(ancestor_path)

        self._wire_new_simulation(sim)
        self._current_file = None
        self._update_title()

    def _wire_new_simulation(self, sim: Simulation) -> None:
        """Attach a new Simulation to the controller and reset all UI state."""
        self._controller.stop()
        self._controller = SimulationController(sim)

        # Re-wire tick bridge
        self._tick_bridge = _TickBridge()
        self._controller.on_tick(self._tick_bridge.tick_occurred.emit)
        self._tick_bridge.tick_occurred.connect(self._on_tick, Qt.ConnectionType.QueuedConnection)

        # Reset IPS tracking
        self._last_ips_time = time.monotonic()
        self._last_ips_inst = 0
        self._current_ips = 0.0

        # Apply current speed
        self._on_speed_changed(self._speed_slider.value())

        # Clear tabs for new soup
        self._selected_addr = None
        self._debug_tab.set_cell(None)
        self._inspect_tab.set_genotype(None)
        self._inventory_tab.clear()
        self._graph_tab.clear()

        # Bind settings tabs to new controller
        self._mutation_tab.set_controller(self._controller)
        self._selection_tab.set_controller(self._controller)
        self._other_settings_tab.set_controller(self._controller)

        # Update genebank window if open
        if self._genebank_window is not None:
            self._genebank_window.set_controller(self._controller)

        # Initial render
        self._update_ui()

    def _update_title(self) -> None:
        if self._current_file:
            self.setWindowTitle(f"PyTierra - {Path(self._current_file).name}")
        else:
            self.setWindowTitle("PyTierra")

    # --- Playback controls ---

    def _on_play_toggled(self, checked: bool) -> None:
        if checked:
            self._play_action.setText("Pause")
            self._play_pause_menu_action.setText("&Pause")
            self._last_ips_time = time.monotonic()
            self._last_ips_inst = self._controller.inst_executed
            self._controller.start()
            self._refresh_timer.start()
        else:
            self._play_action.setText("Play")
            self._play_pause_menu_action.setText("&Play")
            self._controller.pause()
            self._refresh_timer.stop()

    def _toggle_play_pause(self) -> None:
        self._play_action.setChecked(not self._play_action.isChecked())

    def _on_step(self) -> None:
        self._controller.step()
        self._update_ui()

    def _on_speed_changed(self, value: int) -> None:
        slices = int(10 ** (value / 25.0))
        self._controller.set_speed(slices)
        self._speed_label.setText(f" {slices:,} sl/tick")

    def _speed_up(self) -> None:
        self._speed_slider.setValue(min(100, self._speed_slider.value() + 5))

    def _speed_down(self) -> None:
        self._speed_slider.setValue(max(0, self._speed_slider.value() - 5))

    def _on_tick(self) -> None:
        """Called from Qt main thread when simulation completes a tick."""
        pass  # _update_ui handles refresh via QTimer

    # --- UI refresh ---

    def _update_ui(self) -> None:
        """Refresh soup view and status bar from controller state."""
        if self._controller.simulation is None:
            return

        # Soup image
        rgba = self._controller.get_soup_image(self._soup_view.grid_width)
        soup_size = self._controller.simulation.config.soup_size

        # Get all cells once (reused for overlays and status bar count)
        needs_overlays = (self._show_cells_action.isChecked() or
                          self._show_ips_action.isChecked() or
                          self._show_fecundity_action.isChecked())
        cells = self._controller.get_all_cells() if (needs_overlays or self._controller.simulation) else []

        # Update cell overlay data if any overlay is active
        if needs_overlays:
            self._soup_view.set_cell_data([
                (c.pos, c.size, c.ip, c.genotype) for c in cells
            ])
        else:
            if not cells:
                cells = self._controller.get_all_cells()
            self._soup_view.set_cell_data([])

        self._soup_view.update_image(rgba, soup_size)

        # Status bar metrics
        inst = self._controller.inst_executed
        num_cells = len(cells)

        now = time.monotonic()
        dt = now - self._last_ips_time
        if dt >= 0.5:
            self._current_ips = (inst - self._last_ips_inst) / dt
            self._last_ips_time = now
            self._last_ips_inst = inst

        fullness = 0.0
        if self._controller.simulation:
            total_free = self._controller.simulation.soup.total_free()
            fullness = (1.0 - total_free / soup_size) * 100.0

        self._status_bar.update_metrics(inst, num_cells, fullness, self._current_ips)

        # Refresh only the currently visible tab
        current_tab = self._tabs.currentIndex()
        if current_tab == 0:  # Debug
            self._debug_tab.refresh(self._controller)
        elif current_tab == 2:  # Inventory
            self._inventory_tab.refresh(self._controller)
        elif current_tab == 3:  # Graphs
            self._graph_tab.refresh(self._controller)

        # Periodic genebank auto-collection (~every 2 seconds)
        self._auto_collect_counter += 1
        if self._auto_collect_counter >= 60:
            self._auto_collect_counter = 0
            if self._genebank_window is not None:
                self._genebank_window.auto_collect(self._controller)

    def _update_overlays(self) -> None:
        self._soup_view.set_overlays(
            self._show_cells_action.isChecked(),
            self._show_ips_action.isChecked(),
            self._show_fecundity_action.isChecked(),
        )
        self._update_ui()

    # --- Save / Open / Recent ---

    def _save_session(self) -> None:
        if self._current_file:
            self._do_save(self._current_file)
        else:
            self._save_session_as()

    def _save_session_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Session", "", "PyTierra Sessions (*.pytierra)"
        )
        if path:
            if not path.endswith(".pytierra"):
                path += ".pytierra"
            self._do_save(path)

    def _do_save(self, path: str) -> None:
        if self._controller.simulation is None:
            return
        was_running = self._controller.is_running
        if was_running:
            self._controller.pause()
        try:
            save_state(self._controller.simulation, path)
            self._current_file = path
            self._update_title()
            self._add_recent_file(path)
            self._status_bar.showMessage(f"Saved: {Path(path).name}", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Could not save session:\n{e}")
        finally:
            if was_running:
                self._controller.start()

    def _open_session(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Session", "", "PyTierra Sessions (*.pytierra)"
        )
        if path:
            self._do_open(path)

    def _do_open(self, path: str) -> None:
        was_running = self._controller.is_running
        if was_running:
            self._controller.pause()
            self._play_action.setChecked(False)
        try:
            sim = load_state(path)
            self._wire_new_simulation(sim)
            self._current_file = path
            self._update_title()
            self._add_recent_file(path)
            self._status_bar.showMessage(f"Opened: {Path(path).name}", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Open Error", f"Could not open session:\n{e}")

    def _add_recent_file(self, path: str) -> None:
        settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
        recent = settings.value("recent_files", []) or []
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        recent = recent[:_MAX_RECENT_FILES]
        settings.setValue("recent_files", recent)
        self._update_recent_menu()

    def _update_recent_menu(self) -> None:
        self._recent_menu.clear()
        settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
        recent = settings.value("recent_files", []) or []
        if not recent:
            action = QAction("(No recent files)", self)
            action.setEnabled(False)
            self._recent_menu.addAction(action)
            return
        for filepath in recent:
            name = Path(filepath).name
            action = QAction(name, self)
            action.setToolTip(filepath)
            action.triggered.connect(lambda checked, p=filepath: self._do_open(p))
            self._recent_menu.addAction(action)

    # --- Export ---

    def _export_png(self) -> None:
        if self._soup_view._image is None:
            QMessageBox.information(self, "Export", "No soup image to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Soup Image", "soup.png", "PNG Images (*.png)"
        )
        if path:
            self._soup_view._image.save(path, "PNG")
            self._status_bar.showMessage(f"Exported: {Path(path).name}", 3000)

    def _export_csv(self) -> None:
        dc = self._controller.data_collector
        series = dc.all_series()
        if not series or all(len(s) == 0 for s in series.values()):
            QMessageBox.information(self, "Export", "No graph data to export yet.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Graph Data", "pytierra_data.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        # Align all series by time
        all_times = set()
        for s in series.values():
            all_times.update(s.times())
        sorted_times = sorted(all_times)
        # Build lookup for each series
        series_data = {}
        for name, s in series.items():
            series_data[name] = dict(zip(s.times(), s.values()))
        names = list(series.keys())
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["instruction_count"] + names)
            for t in sorted_times:
                row = [t] + [series_data[n].get(t, "") for n in names]
                writer.writerow(row)
        self._status_bar.showMessage(f"Exported: {Path(path).name}", 3000)

    # --- Signal handlers ---

    def _on_address_hovered(self, addr: int) -> None:
        cell = self._controller.get_cell_at(addr)
        if cell is not None:
            self._status_bar.show_hover_info(addr, cell.genotype, cell.size)
        else:
            self._status_bar.show_hover_info(addr)

    def _on_cell_selected(self, addr: int) -> None:
        self._selected_addr = addr
        cell = self._controller.get_cell_at(addr)
        self._debug_tab.set_cell(cell)
        if cell is not None:
            self._status_bar.show_hover_info(addr, cell.genotype, cell.size)
            self._debug_tab.refresh(self._controller)
            gt = self._controller.get_genotype(cell.genotype)
            self._inspect_tab.set_genotype(gt)
            self._tabs.setCurrentIndex(0)  # Switch to Debug tab

    def _on_genotype_selected(self, name: str) -> None:
        gt = self._controller.get_genotype(name)
        self._inspect_tab.set_genotype(gt)
        self._tabs.setCurrentIndex(1)  # Switch to Inspect tab

    # --- Windows ---

    def _show_genebank(self) -> None:
        if self._genebank_window is None:
            self._genebank_window = GenebankWindow(self)
            self._genebank_window.inject_requested.connect(self._on_genebank_inject)
        self._genebank_window.set_controller(self._controller)
        self._genebank_window.show()
        self._genebank_window.raise_()
        self._genebank_window.activateWindow()

    def _on_genebank_inject(self, name: str, genome: bytes) -> None:
        if self._controller.simulation is None:
            return
        import random
        soup_size = self._controller.simulation.config.soup_size
        pos = random.randint(0, soup_size - 1)
        success = self._controller.inject_genome(genome, pos)
        if success:
            self._update_ui()

    def _show_help(self) -> None:
        if self._help_window is None:
            self._help_window = HelpWindow(self)
        self._help_window.show()
        self._help_window.raise_()
        self._help_window.activateWindow()

    def _show_about(self) -> None:
        QMessageBox.about(
            self, "About PyTierra",
            f"<h3>PyTierra v{pytierra.__version__}</h3>"
            f"<p>Python reimplementation of Tom Ray's "
            f"Tierra 6.02 artificial life simulator.</p>"
            f"<p>Based on the original Tierra system created by "
            f"<b>Thomas S. Ray</b> at the University of Oklahoma.</p>"
            f'<p><a href="http://life.ou.edu/tierra/">Original Tierra Project</a></p>'
        )

    def closeEvent(self, event) -> None:
        self._refresh_timer.stop()
        self._controller.stop()
        if self._genebank_window is not None:
            self._genebank_window.close()
        if self._help_window is not None:
            self._help_window.close()
        super().closeEvent(event)


def _apply_dark_palette(app: QApplication) -> None:
    """Apply a dark color palette to the application."""
    palette = QPalette()
    dark = QColor(53, 53, 53)
    darker = QColor(35, 35, 35)
    text = QColor(200, 200, 200)
    highlight = QColor(42, 130, 218)
    disabled_text = QColor(127, 127, 127)

    palette.setColor(QPalette.ColorRole.Window, dark)
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Base, darker)
    palette.setColor(QPalette.ColorRole.AlternateBase, dark)
    palette.setColor(QPalette.ColorRole.ToolTipBase, dark)
    palette.setColor(QPalette.ColorRole.ToolTipText, text)
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.Button, dark)
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Link, highlight)
    palette.setColor(QPalette.ColorRole.Highlight, highlight)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))

    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, disabled_text)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled_text)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled_text)

    app.setPalette(palette)


def _is_dark_mode(app: QApplication) -> bool:
    """Detect if the system is in dark mode."""
    # Qt 6.5+ has styleHints().colorScheme()
    hints = app.styleHints()
    if hasattr(hints, "colorScheme"):
        from PySide6.QtCore import Qt as QtConst
        if hasattr(QtConst, "ColorScheme"):
            return hints.colorScheme() == QtConst.ColorScheme.Dark
    # Fallback: check palette brightness
    bg = app.palette().color(QPalette.ColorRole.Window)
    return bg.lightnessF() < 0.5


def run_gui() -> int:
    """Launch the PyTierra GUI application."""
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("PyTierra")
    app.setOrganizationName(_SETTINGS_ORG)

    if _is_dark_mode(app):
        _apply_dark_palette(app)

    window = MainWindow()
    window.show()

    return app.exec()
