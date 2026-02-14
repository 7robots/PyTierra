"""Time-slice scheduler (slicer queue)."""

import collections
import math
import random
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .cell import Cell
    from .config import Config


class Scheduler:
    def __init__(self, config: Optional["Config"] = None):
        self.queue: collections.deque["Cell"] = collections.deque()
        self._current_idx: int = 0
        self._config = config

    def compute_slice_size(self, cell: "Cell") -> int:
        """Compute the slice size for a given cell based on config."""
        if self._config is None:
            return 25

        if not self._config.siz_dep_slice:
            base = self._config.slice_size
        else:
            # Size-dependent: base = cell_size ^ slice_pow
            base = int(math.pow(cell.mm.size, self._config.slice_pow))

        # SliceStyle 2: fixed fraction + random fraction
        if self._config.slice_style == 2:
            fixed = self._config.slic_fix_frac * base
            rand_part = random.random() * self._config.slic_ran_frac * base
            return max(1, int(fixed + rand_part))

        return max(1, base)

    def add(self, cell: "Cell") -> None:
        self.queue.append(cell)

    def remove(self, cell: "Cell") -> None:
        try:
            idx = None
            for i, c in enumerate(self.queue):
                if c is cell:
                    idx = i
                    break
            if idx is not None:
                del self.queue[idx]
                # Adjust current index if needed
                if idx < self._current_idx:
                    self._current_idx -= 1
                elif idx == self._current_idx and self._current_idx >= len(self.queue):
                    self._current_idx = 0
        except (ValueError, IndexError):
            pass

    def current(self) -> Optional["Cell"]:
        if not self.queue:
            return None
        if self._current_idx >= len(self.queue):
            self._current_idx = 0
        return self.queue[self._current_idx]

    def advance(self) -> None:
        if self.queue:
            self._current_idx = (self._current_idx + 1) % len(self.queue)

    @property
    def num_cells(self) -> int:
        return len(self.queue)
