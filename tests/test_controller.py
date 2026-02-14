"""Tests for the simulation controller."""

import os
import time

from pytierra.config import Config
from pytierra.simulation import Simulation
from pytierra.controller import SimulationController, CellSnapshot

ANCESTOR_PATH = os.path.join(
    os.path.dirname(__file__), "..", "Tierra6_02", "tierra", "gb0", "0080aaa.tie"
)


class TestController:
    def _make_sim(self):
        config = Config()
        config.soup_size = 10000
        sim = Simulation(config=config)
        sim.boot(ANCESTOR_PATH)
        return sim

    def test_step(self):
        sim = self._make_sim()
        ctrl = SimulationController(sim)
        before = ctrl.inst_executed
        ctrl.step(1)
        assert ctrl.inst_executed > before

    def test_get_all_cells(self):
        sim = self._make_sim()
        ctrl = SimulationController(sim)
        cells = ctrl.get_all_cells()
        assert len(cells) == 1
        assert isinstance(cells[0], CellSnapshot)
        assert cells[0].alive is True
        assert cells[0].size == 80

    def test_get_cell(self):
        sim = self._make_sim()
        ctrl = SimulationController(sim)
        cells = ctrl.get_all_cells()
        cell = ctrl.get_cell(cells[0].cell_id)
        assert cell is not None
        assert cell.cell_id == cells[0].cell_id

    def test_start_pause_stop(self):
        sim = self._make_sim()
        ctrl = SimulationController(sim)
        ctrl.set_speed(50)
        ctrl.start()
        time.sleep(0.05)
        assert ctrl.is_running
        ctrl.pause()
        assert not ctrl.is_running
        inst_at_pause = ctrl.inst_executed
        time.sleep(0.02)
        # Instructions should not advance while paused
        assert ctrl.inst_executed == inst_at_pause
        ctrl.stop()

    def test_get_soup_image(self):
        sim = self._make_sim()
        ctrl = SimulationController(sim)
        img = ctrl.get_soup_image(width=100)
        assert img.shape[1] == 100
        assert img.shape[2] == 4  # RGBA
        assert img.dtype.name == "uint8"

    def test_inject_genome(self):
        sim = self._make_sim()
        ctrl = SimulationController(sim)
        genome = bytes([0] * 20)
        result = ctrl.inject_genome(genome, 0)
        assert result is True
        cells = ctrl.get_all_cells()
        assert len(cells) == 2

    def test_update_config(self):
        sim = self._make_sim()
        ctrl = SimulationController(sim)
        ctrl.update_config(slice_size=50)
        assert sim.config.slice_size == 50

    def test_on_tick_callback(self):
        sim = self._make_sim()
        ctrl = SimulationController(sim)
        ticks = []
        ctrl.on_tick(lambda: ticks.append(1))
        ctrl.set_speed(10)
        ctrl.start()
        time.sleep(0.05)
        ctrl.stop()
        assert len(ticks) > 0
