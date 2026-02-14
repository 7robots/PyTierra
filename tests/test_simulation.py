"""Integration tests for full simulation runs."""

import os
import pytest
from pytierra.config import Config
from pytierra.simulation import Simulation


ANCESTOR_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "genomes", "0080aaa.tie"
)


@pytest.mark.skipif(not os.path.exists(ANCESTOR_PATH), reason="Ancestor genome not found")
class TestSimulation:
    def test_run_1m_instructions(self):
        """Run for 1M instructions — population should be >1 and no crashes."""
        config = Config()
        config.soup_size = 60000
        config.seed = 42
        config.gen_per_bkg_mut = 32
        config.gen_per_flaw = 32
        sim = Simulation(config=config)
        sim.boot(ANCESTOR_PATH)
        sim.run(max_instructions=1_000_000, report_interval=500_000)
        assert sim.scheduler.num_cells > 1
        assert sim.inst_executed >= 1_000_000

    def test_config_loading(self):
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "config", "si0"
        )
        if os.path.exists(config_path):
            config = Config.load(config_path)
            assert config.soup_size == 60000
            assert config.slice_size == 25
            assert config.search_limit == 5

    def test_report(self):
        config = Config()
        config.soup_size = 10000
        config.seed = 1
        sim = Simulation(config=config)
        sim.boot(ANCESTOR_PATH)
        report = sim.report()
        assert "Cells: 1" in report
        assert "InstExe:" in report
