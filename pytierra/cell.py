"""Cell: memory regions, CPU, demographics."""

from dataclasses import dataclass, field
from typing import Optional

from .cpu import CPU


@dataclass
class MemRegion:
    pos: int
    size: int


@dataclass
class Demographics:
    genotype: str = ""
    parent_genotype: str = ""
    fecundity: int = 0
    inst_executed: int = 0
    rep_inst: int = 0
    mutations: int = 0
    mov_daught: int = 0
    mov_off_min: int = 0
    mov_off_max: int = 0
    birth_time: int = 0


class Cell:
    __slots__ = ("cpu", "mm", "md", "d", "alive", "ib", "_id")

    _next_id: int = 0

    def __init__(self, pos: int, size: int):
        self.cpu = CPU()
        self.mm = MemRegion(pos, size)
        self.md: Optional[MemRegion] = None
        self.d = Demographics()
        self.alive = True
        self.ib = 0  # instruction bank (remaining in current slice)
        self._id = Cell._next_id
        Cell._next_id += 1

    def owns_mother(self, addr: int, soup_size: int) -> bool:
        """Check if addr falls within mother memory (with wrapping)."""
        addr = addr % soup_size
        start = self.mm.pos % soup_size
        end = (self.mm.pos + self.mm.size) % soup_size
        if start < end:
            return start <= addr < end
        else:  # wraps around
            return addr >= start or addr < end

    def owns_daughter(self, addr: int, soup_size: int) -> bool:
        """Check if addr falls within daughter memory (with wrapping)."""
        if self.md is None:
            return False
        addr = addr % soup_size
        start = self.md.pos % soup_size
        end = (self.md.pos + self.md.size) % soup_size
        if start < end:
            return start <= addr < end
        else:  # wraps around
            return addr >= start or addr < end
