"""Critical test: verify 0080aaa self-replicates correctly."""

import os
import pytest
from pytierra.config import Config
from pytierra.simulation import Simulation
from pytierra.genome_io import load_genome


ANCESTOR_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "genomes", "0080aaa.tie"
)


@pytest.fixture
def ancestor_sim():
    """Create a simulation with the ancestor organism loaded."""
    config = Config()
    config.soup_size = 60000
    config.rate_flaw = 0  # no flaws for deterministic testing
    config.rate_mut = 0   # no background mutations
    config.rate_mov_mut = 0  # no copy mutations
    config.gen_per_bkg_mut = 0
    config.gen_per_flaw = 0
    config.gen_per_mov_mut = 0
    config.gen_per_div_mut = 0
    config.gen_per_ins_ins = 0
    config.gen_per_del_ins = 0
    config.seed = 42
    sim = Simulation(config=config)
    sim.mutations = None  # disable all mutations for determinism
    sim.boot(ANCESTOR_PATH)
    return sim


@pytest.mark.skipif(not os.path.exists(ANCESTOR_PATH), reason="Ancestor genome not found")
class TestAncestorReplication:
    def test_genome_loads_correctly(self):
        genome = load_genome(ANCESTOR_PATH)
        assert len(genome) == 80

    def test_ancestor_boots(self, ancestor_sim):
        sim = ancestor_sim
        assert sim.scheduler.num_cells == 1
        cell = sim.scheduler.current()
        assert cell.mm.size == 80

    def test_first_replication(self, ancestor_sim):
        """After ~827 instructions the ancestor should produce an identical daughter."""
        sim = ancestor_sim

        # Run enough instructions for first replication
        # The .tie file says: 1st_daughter: inst: 827
        for _ in range(50):  # 50 slices * 25 inst = 1250 instructions max
            cell = sim.scheduler.current()
            if cell is None:
                break
            sim.run_slice(cell)
            sim.scheduler.advance()
            if sim.scheduler.num_cells >= 2:
                break

        assert sim.scheduler.num_cells >= 2, (
            f"Expected 2+ cells after {sim.inst_executed} instructions, "
            f"got {sim.scheduler.num_cells}"
        )

        # Verify daughter has identical genome
        original_genome = load_genome(ANCESTOR_PATH)
        cells = list(sim.scheduler.queue)
        mother = cells[0]
        daughter = cells[1]

        mother_genome = sim.soup.read_block(mother.mm.pos, mother.mm.size)
        daughter_genome = sim.soup.read_block(daughter.mm.pos, daughter.mm.size)

        assert len(daughter_genome) == 80
        assert daughter_genome == original_genome, (
            f"Daughter genome differs from ancestor"
        )

    def test_second_replication(self, ancestor_sim):
        """After enough instructions, both mother and daughter should have reproduced."""
        sim = ancestor_sim

        for _ in range(200):  # enough slices for 2+ replications with round-robin
            cell = sim.scheduler.current()
            if cell is None:
                break
            sim.run_slice(cell)
            sim.scheduler.advance()
            if sim.scheduler.num_cells >= 3:
                break

        assert sim.scheduler.num_cells >= 3, (
            f"Expected 3+ cells after {sim.inst_executed} instructions, "
            f"got {sim.scheduler.num_cells}"
        )

    def test_long_run_stability(self, ancestor_sim):
        """Run for 10K instructions — population should grow and stay stable."""
        sim = ancestor_sim
        for _ in range(500):
            cell = sim.scheduler.current()
            if cell is None:
                break
            sim.run_slice(cell)
            sim.scheduler.advance()

        assert sim.scheduler.num_cells >= 2
        assert sim.inst_executed > 5000
