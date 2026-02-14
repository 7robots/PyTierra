"""Reaper queue (selective death)."""

import collections
import random
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .cell import Cell
    from .simulation import Simulation


class Reaper:
    def __init__(self, config):
        self.config = config
        self.queue: collections.deque["Cell"] = collections.deque()

    def add(self, cell: "Cell") -> None:
        self.queue.append(cell)

    def remove(self, cell: "Cell") -> None:
        try:
            self.queue.remove(cell)
        except ValueError:
            pass

    def reap(self, sim: "Simulation", suggested_addr: int = -1) -> Optional["Cell"]:
        """Kill a cell and return it.

        Args:
            sim: simulation context
            suggested_addr: if MalReapTol is set, prefer reaping near this address
        """
        if not self.queue:
            return None

        current_cell = sim.scheduler.current()

        # Near-address mode: try to find oldest cell within MalTol of suggested_addr
        if self.config.mal_reap_tol and suggested_addr >= 0:
            victim = self._reap_near_address(sim, suggested_addr, current_cell)
            if victim is not None:
                return victim

        # Global mode: select from top ReapRndProp fraction of queue
        reap_range = max(1, int(len(self.queue) * self.config.reap_rnd_prop))
        if reap_range < 2:
            idx = 0
        else:
            idx = random.randint(0, reap_range - 1)

        victim = self.queue[idx]

        # Never reap currently executing cell
        if victim is current_cell and len(self.queue) > 1:
            idx = (idx + 1) % min(reap_range, len(self.queue))
            victim = self.queue[idx]
            if victim is current_cell:
                return None

        self._reap_cell(victim, sim)
        return victim

    def _reap_near_address(self, sim: "Simulation", addr: int,
                           current_cell: Optional["Cell"]) -> Optional["Cell"]:
        """Try to reap the oldest cell within MalTol*avg_size of addr."""
        avg_size = 80
        if sim.scheduler.num_cells > 0:
            avg_size = sum(c.mm.size for c in sim.scheduler.queue) // sim.scheduler.num_cells
        max_dist = self.config.mal_tol * avg_size

        # Search the reaper queue from oldest (front) for a nearby cell
        for cell in self.queue:
            if cell is current_cell:
                continue
            dist = min(abs(cell.mm.pos - addr),
                       sim.config.soup_size - abs(cell.mm.pos - addr))
            if dist <= max_dist:
                self._reap_cell(cell, sim)
                return cell
        return None

    def _reap_cell(self, cell: "Cell", sim: "Simulation") -> None:
        """Remove a cell from the simulation."""
        cell.alive = False

        # Emit event before cleanup
        sim.events.emit("CELL_DIED", cell=cell, cause="reaper")

        # Deallocate mother memory
        sim.soup.deallocate(cell.mm.pos, cell.mm.size)
        sim.soup.randomize_block(cell.mm.pos, cell.mm.size)
        sim.soup.remove_owner(cell)

        # Deallocate daughter if present
        if cell.md is not None:
            sim.soup.deallocate(cell.md.pos, cell.md.size)
            cell.md = None

        # Unregister from genebank
        if sim.genebank is not None:
            sim.genebank.unregister(cell)

        # Remove from queues
        self.remove(cell)
        sim.scheduler.remove(cell)

    def check_lazy(self, cell: "Cell", sim: "Simulation") -> bool:
        """Kill cell if it hasn't reproduced in too long. Returns True if reaped."""
        if self.config.lazy_tol <= 0:
            return False
        if cell.d.fecundity > 0:
            threshold = cell.mm.size * self.config.lazy_tol
            if cell.d.rep_inst > threshold:
                self._reap_cell(cell, sim)
                return True
        return False

    def disturbance(self, sim: "Simulation") -> int:
        """Kill a random fraction of the population. Returns number killed."""
        if not self.queue:
            return 0
        num_to_kill = max(1, int(len(self.queue) * self.config.dist_prop))
        killed = 0
        current_cell = sim.scheduler.current()
        for _ in range(num_to_kill):
            if len(self.queue) <= 1:
                break
            idx = random.randint(0, len(self.queue) - 1)
            victim = self.queue[idx]
            if victim is current_cell:
                continue
            self._reap_cell(victim, sim)
            killed += 1
        return killed
