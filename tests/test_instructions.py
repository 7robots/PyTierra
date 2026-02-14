"""Unit tests for individual instructions."""

import pytest
from pytierra.config import Config
from pytierra.soup import Soup
from pytierra.cell import Cell
from pytierra.scheduler import Scheduler
from pytierra.simulation import Simulation
from pytierra.instructions import (
    nop, not0, shl, zero, ifz, sub_cab, sub_aac,
    inc_a, inc_b, dec_c, inc_c,
    push_a, push_b, push_c, push_d,
    pop_a, pop_b, pop_c, pop_d,
    mov_dc, mov_ba, movii, ret,
    mal, divide,
)


def make_sim(soup_size=1000):
    config = Config()
    config.soup_size = soup_size
    config.rate_flaw = 0  # disable flaws for deterministic tests
    config.rate_mov_mut = 0
    config.rate_mut = 0
    sim = Simulation(config=config)
    return sim


def make_cell(sim, pos=100, size=80):
    cell = Cell(pos, size)
    cell.cpu.ip = pos
    sim.soup.allocate_at(pos, size)
    sim.scheduler.add(cell)
    sim.soup.add_owner(cell)
    return cell


class TestArithmetic:
    def test_zero(self):
        sim = make_sim()
        cell = make_cell(sim)
        cell.cpu.cx = 42
        zero(sim, cell)
        assert cell.cpu.cx == 0
        assert cell.cpu.flag_z is True

    def test_not0(self):
        sim = make_sim()
        cell = make_cell(sim)
        cell.cpu.cx = 0
        not0(sim, cell)
        assert cell.cpu.cx == 1

    def test_not0_flip(self):
        sim = make_sim()
        cell = make_cell(sim)
        cell.cpu.cx = 1
        not0(sim, cell)
        assert cell.cpu.cx == 0
        assert cell.cpu.flag_z is True

    def test_shl(self):
        sim = make_sim()
        cell = make_cell(sim)
        cell.cpu.cx = 1
        shl(sim, cell)
        assert cell.cpu.cx == 2
        shl(sim, cell)
        assert cell.cpu.cx == 4

    def test_inc_a(self):
        sim = make_sim()
        cell = make_cell(sim)
        cell.cpu.ax = 5
        inc_a(sim, cell)
        assert cell.cpu.ax == 6

    def test_inc_b(self):
        sim = make_sim()
        cell = make_cell(sim)
        cell.cpu.bx = 10
        inc_b(sim, cell)
        assert cell.cpu.bx == 11

    def test_dec_c(self):
        sim = make_sim()
        cell = make_cell(sim)
        cell.cpu.cx = 5
        dec_c(sim, cell)
        assert cell.cpu.cx == 4

    def test_inc_c(self):
        sim = make_sim()
        cell = make_cell(sim)
        cell.cpu.cx = 3
        inc_c(sim, cell)
        assert cell.cpu.cx == 4

    def test_sub_cab(self):
        sim = make_sim()
        cell = make_cell(sim)
        cell.cpu.ax = 10
        cell.cpu.bx = 3
        sub_cab(sim, cell)
        assert cell.cpu.cx == 7

    def test_sub_aac(self):
        sim = make_sim()
        cell = make_cell(sim)
        cell.cpu.ax = 10
        cell.cpu.cx = 4
        sub_aac(sim, cell)
        assert cell.cpu.ax == 6


class TestStack:
    def test_push_pop_a(self):
        sim = make_sim()
        cell = make_cell(sim)
        cell.cpu.ax = 42
        push_a(sim, cell)
        cell.cpu.ax = 0
        pop_a(sim, cell)
        assert cell.cpu.ax == 42

    def test_push_pop_b(self):
        sim = make_sim()
        cell = make_cell(sim)
        cell.cpu.bx = 99
        push_b(sim, cell)
        cell.cpu.bx = 0
        pop_b(sim, cell)
        assert cell.cpu.bx == 99

    def test_push_pop_c(self):
        sim = make_sim()
        cell = make_cell(sim)
        cell.cpu.cx = 55
        push_c(sim, cell)
        cell.cpu.cx = 0
        pop_c(sim, cell)
        assert cell.cpu.cx == 55

    def test_push_pop_d(self):
        sim = make_sim()
        cell = make_cell(sim)
        cell.cpu.dx = 77
        push_d(sim, cell)
        cell.cpu.dx = 0
        pop_d(sim, cell)
        assert cell.cpu.dx == 77

    def test_stack_order(self):
        """LIFO order: push a, push b, pop c should give b's value."""
        sim = make_sim()
        cell = make_cell(sim)
        cell.cpu.ax = 1
        cell.cpu.bx = 2
        push_a(sim, cell)
        push_b(sim, cell)
        pop_c(sim, cell)
        assert cell.cpu.cx == 2
        pop_c(sim, cell)
        assert cell.cpu.cx == 1


class TestMoves:
    def test_mov_dc(self):
        sim = make_sim()
        cell = make_cell(sim)
        cell.cpu.cx = 42
        mov_dc(sim, cell)
        assert cell.cpu.dx == 42

    def test_mov_ba(self):
        sim = make_sim()
        cell = make_cell(sim)
        cell.cpu.ax = 100
        mov_ba(sim, cell)
        assert cell.cpu.bx == 100


class TestIfz:
    def test_ifz_zero_doesnt_skip(self):
        sim = make_sim()
        cell = make_cell(sim)
        cell.cpu.cx = 0
        old_ip = cell.cpu.ip
        ifz(sim, cell)
        # cx == 0: don't skip, ip unchanged (main loop will increment)
        assert cell.cpu.ip == old_ip

    def test_ifz_nonzero_skips(self):
        sim = make_sim()
        cell = make_cell(sim)
        cell.cpu.cx = 5
        old_ip = cell.cpu.ip
        ifz(sim, cell)
        # cx != 0: skip next instruction
        assert cell.cpu.ip == old_ip + 1


class TestRet:
    def test_ret(self):
        sim = make_sim()
        cell = make_cell(sim)
        cell.cpu.push(200)
        ret(sim, cell)
        assert cell.cpu.ip == 200
        assert cell.cpu._ip_modified is True


class TestMal:
    def test_mal_basic(self):
        sim = make_sim(soup_size=10000)
        cell = make_cell(sim, pos=100, size=80)
        cell.cpu.cx = 80
        mal(sim, cell)
        assert cell.md is not None
        assert cell.md.size == 80
        assert cell.cpu.ax == cell.md.pos
        assert cell.cpu.flag_e is False

    def test_mal_too_small(self):
        sim = make_sim()
        cell = make_cell(sim)
        cell.cpu.cx = 5  # below min_cell_size
        mal(sim, cell)
        assert cell.md is None
        assert cell.cpu.flag_e is True

    def test_mal_too_large(self):
        sim = make_sim()
        cell = make_cell(sim, size=80)
        cell.cpu.cx = 200  # > 2 * mother size
        mal(sim, cell)
        assert cell.md is None
        assert cell.cpu.flag_e is True


class TestMovii:
    def test_movii_to_daughter(self):
        sim = make_sim(soup_size=10000)
        cell = make_cell(sim, pos=100, size=80)
        # Allocate daughter manually
        from pytierra.cell import MemRegion
        cell.md = MemRegion(500, 80)
        sim.soup.allocate_at(500, 80)

        # Write something to source
        sim.soup.write(100, 42)
        cell.cpu.bx = 100  # source
        cell.cpu.ax = 500  # dest (in daughter)
        movii(sim, cell)
        assert sim.soup.read(500) == 42
        assert cell.cpu.flag_e is False
        assert cell.d.mov_daught == 1

    def test_movii_outside_daughter_fails(self):
        sim = make_sim(soup_size=10000)
        cell = make_cell(sim, pos=100, size=80)
        from pytierra.cell import MemRegion
        cell.md = MemRegion(500, 80)

        cell.cpu.bx = 100
        cell.cpu.ax = 300  # NOT in daughter
        movii(sim, cell)
        assert cell.cpu.flag_e is True
        assert cell.d.mov_daught == 0


class TestDivide:
    def test_divide_no_daughter(self):
        sim = make_sim()
        cell = make_cell(sim)
        cell.md = None
        divide(sim, cell)
        assert cell.cpu.flag_e is True

    def test_divide_insufficient_copy(self):
        sim = make_sim(soup_size=10000)
        cell = make_cell(sim, pos=100, size=80)
        from pytierra.cell import MemRegion
        cell.md = MemRegion(500, 80)
        cell.d.mov_daught = 10  # way below threshold
        divide(sim, cell)
        assert cell.cpu.flag_e is True
