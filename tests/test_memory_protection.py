"""Tests for memory protection system."""

from pytierra.config import Config
from pytierra.soup import Soup, PROT_EXECUTE, PROT_WRITE, PROT_READ
from pytierra.cell import Cell


class TestMemoryProtection:
    def _setup(self):
        config = Config()
        config.soup_size = 1000
        soup = Soup(1000)
        cell_a = Cell(100, 80)
        cell_b = Cell(200, 80)
        soup.add_owner(cell_a)
        soup.add_owner(cell_b)
        return config, soup, cell_a, cell_b

    def test_no_protection_when_all_zero(self):
        config, soup, cell_a, cell_b = self._setup()
        config.mem_mode_free = 0
        config.mem_mode_mine = 0
        config.mem_mode_prot = 0
        assert soup.check_read(200, cell_a, config) is True
        assert soup.check_write(200, cell_a, config) is True
        assert soup.check_execute(200, cell_a, config) is True

    def test_protect_write_other(self):
        config, soup, cell_a, cell_b = self._setup()
        config.mem_mode_prot = PROT_WRITE  # block writes to other's memory
        # cell_a writing to cell_b's memory should be blocked
        assert soup.check_write(200, cell_a, config) is False
        # cell_b writing to own memory should be allowed
        assert soup.check_write(200, cell_b, config) is True
        # Reading still allowed
        assert soup.check_read(200, cell_a, config) is True

    def test_protect_execute_other(self):
        config, soup, cell_a, cell_b = self._setup()
        config.mem_mode_prot = PROT_EXECUTE
        assert soup.check_execute(200, cell_a, config) is False
        assert soup.check_execute(100, cell_a, config) is True

    def test_protect_free_memory(self):
        config, soup, cell_a, cell_b = self._setup()
        config.mem_mode_free = PROT_EXECUTE  # can't execute free memory
        # Address 0 is free (not owned)
        assert soup.check_execute(0, cell_a, config) is False
        assert soup.check_read(0, cell_a, config) is True

    def test_protect_own_memory(self):
        config, soup, cell_a, cell_b = self._setup()
        config.mem_mode_mine = PROT_WRITE  # can't write own memory
        assert soup.check_write(100, cell_a, config) is False
        assert soup.check_read(100, cell_a, config) is True

    def test_combined_protection_bits(self):
        config, soup, cell_a, cell_b = self._setup()
        config.mem_mode_prot = PROT_WRITE | PROT_EXECUTE  # 3
        assert soup.check_write(200, cell_a, config) is False
        assert soup.check_execute(200, cell_a, config) is False
        assert soup.check_read(200, cell_a, config) is True
