"""Tests for the scheduler."""

from pytierra.cell import Cell
from pytierra.scheduler import Scheduler


class TestScheduler:
    def test_add_and_current(self):
        sched = Scheduler()
        cell = Cell(0, 80)
        sched.add(cell)
        assert sched.current() is cell

    def test_round_robin(self):
        sched = Scheduler()
        c1 = Cell(0, 80)
        c2 = Cell(100, 80)
        c3 = Cell(200, 80)
        sched.add(c1)
        sched.add(c2)
        sched.add(c3)

        assert sched.current() is c1
        sched.advance()
        assert sched.current() is c2
        sched.advance()
        assert sched.current() is c3
        sched.advance()
        assert sched.current() is c1  # wraps

    def test_remove(self):
        sched = Scheduler()
        c1 = Cell(0, 80)
        c2 = Cell(100, 80)
        sched.add(c1)
        sched.add(c2)
        sched.remove(c1)
        assert sched.num_cells == 1
        assert sched.current() is c2

    def test_empty(self):
        sched = Scheduler()
        assert sched.current() is None
        assert sched.num_cells == 0
