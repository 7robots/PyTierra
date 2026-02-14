"""Tests for soup memory management."""

import pytest
from pytierra.soup import Soup


class TestReadWrite:
    def test_basic_rw(self):
        soup = Soup(100)
        soup.write(10, 42)
        assert soup.read(10) == 42

    def test_address_wrapping(self):
        soup = Soup(100)
        soup.write(150, 7)
        assert soup.read(50) == 7
        assert soup.read(150) == 7

    def test_read_block(self):
        soup = Soup(100)
        soup.write_block(10, bytes([1, 2, 3, 4, 5]))
        block = soup.read_block(10, 5)
        assert block == bytes([1, 2, 3, 4, 5])

    def test_read_block_wrapping(self):
        soup = Soup(100)
        soup.write_block(98, bytes([10, 20, 30]))
        assert soup.read(98) == 10
        assert soup.read(99) == 20
        assert soup.read(0) == 30
        block = soup.read_block(98, 3)
        assert block == bytes([10, 20, 30])


class TestAllocation:
    def test_allocate_at(self):
        soup = Soup(1000)
        assert soup.allocate_at(100, 80)
        assert not soup.is_free(100)
        assert not soup.is_free(179)
        assert soup.is_free(180)
        assert soup.is_free(99)

    def test_allocate_first_fit(self):
        soup = Soup(1000)
        soup.allocate_at(100, 80)  # block in middle
        result = soup.allocate(50, mode=0)
        assert result is not None
        addr, size = result
        assert size == 50
        assert addr == 0  # first fit: first free block

    def test_allocate_better_fit(self):
        soup = Soup(1000)
        # Create gaps: [0,100), [180, 200), [200, 1000)
        soup.allocate_at(100, 80)
        soup.allocate_at(200, 700)
        # Free blocks: [0,100), [180,200), [900,1000)
        result = soup.allocate(15, mode=1)
        assert result is not None
        addr, size = result
        # Better fit should pick the 20-byte block [180,200)
        assert addr == 180

    def test_deallocate_merge(self):
        soup = Soup(1000)
        soup.allocate_at(100, 80)
        soup.allocate_at(200, 80)
        # Free blocks: [0,100), [180,200), [280,1000)
        assert soup.total_free() == 1000 - 80 - 80

        soup.deallocate(100, 80)
        # Should merge [0,100) + [100,180) + [180,200) = [0,200)
        assert soup.total_free() == 1000 - 80
        # Verify merged
        result = soup.allocate(200, mode=0)
        assert result is not None

    def test_total_free(self):
        soup = Soup(1000)
        assert soup.total_free() == 1000
        soup.allocate_at(100, 80)
        assert soup.total_free() == 920


class TestOwners:
    def test_owner_tracking(self):
        from pytierra.cell import Cell
        soup = Soup(1000)
        cell = Cell(100, 80)
        soup.add_owner(cell)
        assert soup.owner_at(100) is cell
        assert soup.owner_at(150) is cell
        assert soup.owner_at(179) is cell
        assert soup.owner_at(180) is None

    def test_remove_owner(self):
        from pytierra.cell import Cell
        soup = Soup(1000)
        cell = Cell(100, 80)
        soup.add_owner(cell)
        soup.remove_owner(cell)
        assert soup.owner_at(100) is None
