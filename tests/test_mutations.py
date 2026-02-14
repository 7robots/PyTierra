"""Tests for the mutation system."""

import random
import pytest
from pytierra.config import Config
from pytierra.soup import Soup
from pytierra.cell import Cell, MemRegion
from pytierra.mutations import Mutations
from pytierra.simulation import Simulation


class TestBackgroundMutation:
    def test_mutation_changes_soup(self):
        config = Config()
        config.soup_size = 100
        config.mut_bit_prop = 0.0  # always replace (easier to detect)
        sim = Simulation(config=config)

        random.seed(42)
        # Fill soup with zeros
        for i in range(100):
            sim.soup.write(i, 0)

        mutations = Mutations(config)
        # Apply many mutations — at least some should change values
        changed = False
        for _ in range(100):
            mutations.background_mutation(sim)
            for i in range(100):
                if sim.soup.read(i) != 0:
                    changed = True
                    break
            if changed:
                break
        assert changed


class TestMutationRates:
    def test_rate_calculation(self):
        config = Config()
        config.gen_per_bkg_mut = 32
        config.gen_per_flaw = 32
        config.gen_per_mov_mut = 0
        mutations = Mutations(config)
        mutations.update_rates(80, 10)
        assert config.rate_mut == pytest.approx(1.0 / (32 * 80))
        assert config.rate_flaw == pytest.approx(1.0 / (32 * 80))
        assert config.rate_mov_mut == 0.0

    def test_rate_zero_gen(self):
        config = Config()
        config.gen_per_bkg_mut = 0
        mutations = Mutations(config)
        mutations.update_rates(80, 10)
        assert config.rate_mut == 0.0
