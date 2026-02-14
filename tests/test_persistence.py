"""Tests for save/restore simulation state."""

import tempfile
import os

from pytierra.config import Config
from pytierra.simulation import Simulation
from pytierra.persistence import save_state, load_state

ANCESTOR_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "genomes", "0080aaa.tie"
)


class TestPersistence:
    def test_save_restore_roundtrip(self):
        """Save a running sim, restore it, verify state matches."""
        config = Config()
        config.soup_size = 10000
        sim = Simulation(config=config)
        sim.boot(ANCESTOR_PATH)
        sim.run(max_instructions=5000)

        # Capture state before save
        inst_before = sim.inst_executed
        num_cells_before = sim.scheduler.num_cells
        soup_snapshot = bytes(sim.soup.data)

        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            path = f.name

        try:
            save_state(sim, path)
            restored = load_state(path)

            assert restored.inst_executed == inst_before
            assert restored.scheduler.num_cells == num_cells_before
            assert bytes(restored.soup.data) == soup_snapshot
            assert restored.config.soup_size == 10000
        finally:
            os.unlink(path)

    def test_restored_sim_can_continue(self):
        """Verify a restored sim can continue running."""
        config = Config()
        config.soup_size = 10000
        sim = Simulation(config=config)
        sim.boot(ANCESTOR_PATH)
        sim.run(max_instructions=3000)

        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            path = f.name

        try:
            save_state(sim, path)
            restored = load_state(path)
            inst_before = restored.inst_executed
            restored.run(max_instructions=inst_before + 3000)
            assert restored.inst_executed > inst_before
        finally:
            os.unlink(path)

    def test_genebank_preserved(self):
        """Verify genebank genotypes survive save/restore."""
        config = Config()
        config.soup_size = 10000
        sim = Simulation(config=config)
        sim.boot(ANCESTOR_PATH)
        sim.run(max_instructions=5000)

        genotypes_before = set(sim.genebank.genotypes.keys())

        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            path = f.name

        try:
            save_state(sim, path)
            restored = load_state(path)
            genotypes_after = set(restored.genebank.genotypes.keys())
            assert genotypes_before == genotypes_after
        finally:
            os.unlink(path)
