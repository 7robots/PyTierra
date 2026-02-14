"""Memory soup (numpy array) + free list management."""

import bisect
import random
from typing import Optional, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .cell import Cell

# Memory protection bit flags
PROT_EXECUTE = 1
PROT_WRITE = 2
PROT_READ = 4


class Soup:
    def __init__(self, size: int):
        self.size = size
        self.data = np.zeros(size, dtype=np.uint8)
        # Free list: sorted by position, list of [pos, size]
        self.free_blocks: list[list[int]] = [[0, size]]
        # Owner tracking: sorted by position, list of (pos, size, cell)
        self._owners: list[tuple[int, int, "Cell"]] = []

    def read(self, addr: int) -> int:
        return int(self.data[addr % self.size])

    def write(self, addr: int, value: int) -> None:
        self.data[addr % self.size] = value & 0xFF

    def check_read(self, addr: int, reader: "Cell", config) -> bool:
        """Check if reader is allowed to read addr. Returns True if allowed."""
        if config.mem_mode_free == 0 and config.mem_mode_mine == 0 and config.mem_mode_prot == 0:
            return True  # no protection enabled
        return self._check_access(addr, reader, config, PROT_READ)

    def check_write(self, addr: int, writer: "Cell", config) -> bool:
        """Check if writer is allowed to write addr. Returns True if allowed."""
        if config.mem_mode_free == 0 and config.mem_mode_mine == 0 and config.mem_mode_prot == 0:
            return True
        return self._check_access(addr, writer, config, PROT_WRITE)

    def check_execute(self, addr: int, executor: "Cell", config) -> bool:
        """Check if executor is allowed to execute instruction at addr."""
        if config.mem_mode_free == 0 and config.mem_mode_mine == 0 and config.mem_mode_prot == 0:
            return True
        return self._check_access(addr, executor, config, PROT_EXECUTE)

    def _check_access(self, addr: int, cell: "Cell", config, access_bit: int) -> bool:
        """Check memory access permission."""
        addr = addr % self.size
        owner = self.owner_at(addr)
        if owner is None:
            # Free memory
            return not (config.mem_mode_free & access_bit)
        elif owner is cell:
            # Own memory
            return not (config.mem_mode_mine & access_bit)
        else:
            # Another creature's memory
            return not (config.mem_mode_prot & access_bit)

    def read_block(self, addr: int, size: int) -> bytes:
        addr = addr % self.size
        if addr + size <= self.size:
            return bytes(self.data[addr:addr + size])
        # Wrapping read
        part1 = bytes(self.data[addr:])
        part2 = bytes(self.data[:size - (self.size - addr)])
        return part1 + part2

    def write_block(self, addr: int, data: bytes) -> None:
        addr = addr % self.size
        if addr + len(data) <= self.size:
            self.data[addr:addr + len(data)] = np.frombuffer(data, dtype=np.uint8)
        else:
            split = self.size - addr
            self.data[addr:] = np.frombuffer(data[:split], dtype=np.uint8)
            self.data[:len(data) - split] = np.frombuffer(data[split:], dtype=np.uint8)

    def allocate(self, size: int, mode: int = 1, hint_addr: int = -1,
                 tolerance: int = -1) -> Optional[tuple[int, int]]:
        """Allocate a block of memory.

        Args:
            size: number of bytes to allocate
            mode: 0=first fit, 1=better fit, 2=random preference,
                  3=near mother, 4=near bx, 5=near stack top, 6=suggested
            hint_addr: preferred address (for modes 3-6)
            tolerance: max distance from hint_addr to search

        Returns:
            (address, actual_size) or None if no space available.
        """
        if not self.free_blocks:
            return None

        idx = None
        if mode == 0:
            for i, (pos, sz) in enumerate(self.free_blocks):
                if sz >= size:
                    idx = i
                    break
        elif mode == 1:
            best_idx = None
            best_size = float("inf")
            for i, (pos, sz) in enumerate(self.free_blocks):
                if sz >= size and sz < best_size:
                    best_size = sz
                    best_idx = i
            idx = best_idx
        elif mode == 2:
            adequate = [i for i, (pos, sz) in enumerate(self.free_blocks) if sz >= size]
            if adequate:
                idx = random.choice(adequate)
        elif mode in (3, 4, 5, 6) and hint_addr >= 0:
            best_idx = None
            best_dist = float("inf")
            for i, (pos, sz) in enumerate(self.free_blocks):
                if sz >= size:
                    dist = min(abs(pos - hint_addr),
                               self.size - abs(pos - hint_addr))
                    if dist < best_dist:
                        best_dist = dist
                        best_idx = i
            if best_idx is not None:
                if tolerance >= 0 and best_dist > tolerance:
                    idx = None
                else:
                    idx = best_idx
        else:
            return self.allocate(size, mode=1)

        if idx is None:
            return None

        pos, block_size = self.free_blocks[idx]

        if block_size == size:
            self.free_blocks.pop(idx)
        else:
            self.free_blocks[idx] = [pos + size, block_size - size]

        return (pos, size)

    def allocate_at(self, addr: int, size: int) -> bool:
        """Allocate a specific region (used during boot). Returns success."""
        addr = addr % self.size
        for i, (pos, block_size) in enumerate(self.free_blocks):
            if pos <= addr and pos + block_size >= addr + size:
                self.free_blocks.pop(i)
                if pos < addr:
                    self.free_blocks.insert(i, [pos, addr - pos])
                    i += 1
                remainder_start = addr + size
                remainder_size = (pos + block_size) - remainder_start
                if remainder_size > 0:
                    self.free_blocks.insert(i, [remainder_start, remainder_size])
                return True
        return False

    def deallocate(self, addr: int, size: int) -> None:
        """Return a block to the free list, merging adjacent blocks."""
        addr = addr % self.size
        new_block = [addr, size]

        positions = [b[0] for b in self.free_blocks]
        insert_idx = bisect.bisect_left(positions, addr)
        self.free_blocks.insert(insert_idx, new_block)

        # Merge with next block
        if insert_idx + 1 < len(self.free_blocks):
            curr = self.free_blocks[insert_idx]
            nxt = self.free_blocks[insert_idx + 1]
            if curr[0] + curr[1] == nxt[0]:
                curr[1] += nxt[1]
                self.free_blocks.pop(insert_idx + 1)

        # Merge with previous block
        if insert_idx > 0:
            prev = self.free_blocks[insert_idx - 1]
            curr = self.free_blocks[insert_idx]
            if prev[0] + prev[1] == curr[0]:
                prev[1] += curr[1]
                self.free_blocks.pop(insert_idx)

    def randomize_block(self, addr: int, size: int) -> None:
        """Fill a block with random instructions (called after reaping)."""
        for i in range(size):
            self.data[(addr + i) % self.size] = random.randint(0, 31)

    def is_free(self, addr: int) -> bool:
        addr = addr % self.size
        for pos, sz in self.free_blocks:
            if pos <= addr < pos + sz:
                return True
        return False

    def total_free(self) -> int:
        return sum(sz for _, sz in self.free_blocks)

    def add_owner(self, cell: "Cell") -> None:
        """Register a cell as owner of its memory region."""
        positions = [o[0] for o in self._owners]
        idx = bisect.bisect_left(positions, cell.mm.pos)
        self._owners.insert(idx, (cell.mm.pos, cell.mm.size, cell))

    def remove_owner(self, cell: "Cell") -> None:
        """Remove a cell from owner tracking."""
        for i, (pos, sz, c) in enumerate(self._owners):
            if c is cell:
                self._owners.pop(i)
                return

    def owner_at(self, addr: int) -> Optional["Cell"]:
        """Find which cell owns the given address."""
        addr = addr % self.size
        lo, hi = 0, len(self._owners)
        while lo < hi:
            mid = (lo + hi) // 2
            pos, sz, cell = self._owners[mid]
            if addr < pos:
                hi = mid
            elif addr >= pos + sz:
                lo = mid + 1
            else:
                return cell
        return None
