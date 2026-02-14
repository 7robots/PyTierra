"""Mutation, flaw, genetic operators."""

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cell import Cell
    from .simulation import Simulation

NOP0 = 0
NOP1 = 1


class Mutations:
    def __init__(self, config):
        self.config = config

    def update_rates(self, avg_size: int, num_cells: int) -> None:
        """Recalculate mutation rates based on current population."""
        if avg_size <= 0:
            avg_size = 80

        if self.config.gen_per_bkg_mut > 0:
            self.config.rate_mut = 1.0 / (self.config.gen_per_bkg_mut * avg_size)
        else:
            self.config.rate_mut = 0.0

        if self.config.gen_per_flaw > 0:
            self.config.rate_flaw = 1.0 / (self.config.gen_per_flaw * avg_size)
        else:
            self.config.rate_flaw = 0.0

        if self.config.gen_per_mov_mut > 0:
            self.config.rate_mov_mut = 1.0 / (self.config.gen_per_mov_mut * avg_size)
        else:
            self.config.rate_mov_mut = 0.0

    def background_mutation(self, sim: "Simulation") -> None:
        """Apply a single background mutation to a random soup location."""
        addr = random.randint(0, sim.config.soup_size - 1)
        value = sim.soup.read(addr)
        value = self._mutate_value(value)
        sim.soup.write(addr, value)
        sim.events.emit("MUTATION", addr=addr, kind="background")

    def _mutate_value(self, value: int) -> int:
        """Apply a mutation to a single instruction value."""
        if random.random() < self.config.mut_bit_prop:
            value ^= (1 << random.randint(0, 4))
        else:
            value = random.randint(0, 31)
        return value

    def genetic_ops(self, cell: "Cell", sim: "Simulation") -> None:
        """Apply genetic operators to daughter at division.

        Order follows C implementation: point mutations, then crossover,
        then insertion, then deletion — at both instruction and segment level.
        """
        if cell.md is None:
            return

        # 1. Division point mutations
        self._mutation_ops(cell, sim)
        # 2. Same-size crossover at instruction level
        self._crossover_inst_same_size(cell, sim)
        # 3. Size-changing crossover at instruction level
        self._crossover_inst(cell, sim)
        # 4. Instruction insertion
        self._insertion_inst(cell, sim)
        # 5. Instruction deletion
        self._deletion_inst(cell, sim)
        # 6. Segment-level crossover
        self._crossover_seg(cell, sim)
        # 7. Segment insertion
        self._insertion_seg(cell, sim)
        # 8. Segment deletion
        self._deletion_seg(cell, sim)

    def _mutation_ops(self, cell: "Cell", sim: "Simulation") -> None:
        """Point mutations in daughter genome."""
        if self.config.gen_per_div_mut <= 0:
            return
        rate = 1.0 / self.config.gen_per_div_mut
        if random.random() >= rate:
            return
        md = cell.md
        offset = random.randint(0, md.size - 1)
        addr = (md.pos + offset) % sim.config.soup_size
        value = sim.soup.read(addr)
        value = self._mutate_value(value)
        sim.soup.write(addr, value)
        cell.d.mutations += 1

    def _crossover_inst_same_size(self, cell: "Cell", sim: "Simulation") -> None:
        """Exchange instruction segments with a random same-size genome in the soup."""
        if self.config.gen_per_cro_ins_sam_siz <= 0:
            return
        rate = 1.0 / self.config.gen_per_cro_ins_sam_siz
        if random.random() >= rate:
            return

        md = cell.md
        # Find a same-size cell in the population
        mate = self._find_same_size_mate(cell, sim)
        if mate is None:
            return

        # Pick a crossover point and exchange tails
        cross_point = random.randint(1, md.size - 1)
        for i in range(cross_point, md.size):
            d_addr = (md.pos + i) % sim.config.soup_size
            m_addr = (mate.mm.pos + i) % sim.config.soup_size
            # Copy from mate into daughter
            sim.soup.write(d_addr, sim.soup.read(m_addr))
        cell.d.mutations += 1

    def _crossover_inst(self, cell: "Cell", sim: "Simulation") -> None:
        """Size-changing instruction-level crossover with a random genome."""
        if self.config.gen_per_cro_ins <= 0:
            return
        rate = 1.0 / self.config.gen_per_cro_ins
        if random.random() >= rate:
            return

        md = cell.md
        # Find any cell as mate
        if sim.scheduler.num_cells < 2:
            return
        candidates = [c for c in sim.scheduler.queue if c is not cell]
        if not candidates:
            return
        mate = random.choice(candidates)

        # Pick crossover points in each genome
        cross_d = random.randint(1, md.size - 1)
        cross_m = random.randint(1, mate.mm.size - 1)

        # Build new daughter: daughter[:cross_d] + mate[cross_m:]
        tail_len = mate.mm.size - cross_m
        new_size = cross_d + tail_len
        if new_size < self.config.min_cell_size or new_size > md.size:
            return  # can't resize, just write what fits

        # Write mate's tail into daughter starting at cross_d
        write_len = min(tail_len, md.size - cross_d)
        for i in range(write_len):
            d_addr = (md.pos + cross_d + i) % sim.config.soup_size
            m_addr = (mate.mm.pos + cross_m + i) % sim.config.soup_size
            sim.soup.write(d_addr, sim.soup.read(m_addr))
        cell.d.mutations += 1

    def _insertion_inst(self, cell: "Cell", sim: "Simulation") -> None:
        """Insert a random instruction into daughter genome."""
        if self.config.gen_per_ins_ins <= 0:
            return
        rate = 1.0 / self.config.gen_per_ins_ins
        if random.random() >= rate:
            return

        md = cell.md
        if md.size < 2:
            return
        pos = random.randint(0, md.size - 1)
        addr = (md.pos + pos) % sim.config.soup_size
        # Shift everything after pos forward by 1 (within daughter bounds)
        for i in range(md.size - 1, pos, -1):
            src = (md.pos + i - 1) % sim.config.soup_size
            dst = (md.pos + i) % sim.config.soup_size
            sim.soup.write(dst, sim.soup.read(src))
        sim.soup.write(addr, random.randint(0, 31))
        cell.d.mutations += 1

    def _deletion_inst(self, cell: "Cell", sim: "Simulation") -> None:
        """Delete a random instruction from daughter genome."""
        if self.config.gen_per_del_ins <= 0:
            return
        rate = 1.0 / self.config.gen_per_del_ins
        if random.random() >= rate:
            return

        md = cell.md
        if md.size < self.config.min_cell_size + 1:
            return
        pos = random.randint(0, md.size - 1)
        for i in range(pos, md.size - 1):
            src = (md.pos + i + 1) % sim.config.soup_size
            dst = (md.pos + i) % sim.config.soup_size
            sim.soup.write(dst, sim.soup.read(src))
        sim.soup.write((md.pos + md.size - 1) % sim.config.soup_size, 0)
        cell.d.mutations += 1

    def _crossover_seg(self, cell: "Cell", sim: "Simulation") -> None:
        """Segment-level crossover: exchange NOP-bounded segments with a mate."""
        if self.config.gen_per_cro_seg <= 0:
            return
        rate = 1.0 / self.config.gen_per_cro_seg
        if random.random() >= rate:
            return

        md = cell.md
        # Find a mate
        candidates = [c for c in sim.scheduler.queue if c is not cell]
        if not candidates:
            return
        mate = random.choice(candidates)

        # Find segments in daughter and mate
        d_segs = self._find_segments(md.pos, md.size, sim)
        m_segs = self._find_segments(mate.mm.pos, mate.mm.size, sim)
        if not d_segs or not m_segs:
            return

        # Pick a random segment from each and swap
        d_seg = random.choice(d_segs)
        m_seg = random.choice(m_segs)

        # Copy mate segment into daughter segment position (truncate to fit)
        copy_len = min(d_seg[1], m_seg[1])
        for i in range(copy_len):
            d_addr = (d_seg[0] + i) % sim.config.soup_size
            m_addr = (m_seg[0] + i) % sim.config.soup_size
            sim.soup.write(d_addr, sim.soup.read(m_addr))
        cell.d.mutations += 1

    def _insertion_seg(self, cell: "Cell", sim: "Simulation") -> None:
        """Segment insertion: duplicate a random segment within daughter."""
        if self.config.gen_per_ins_seg <= 0:
            return
        rate = 1.0 / self.config.gen_per_ins_seg
        if random.random() >= rate:
            return

        md = cell.md
        segs = self._find_segments(md.pos, md.size, sim)
        if not segs:
            return

        seg = random.choice(segs)
        seg_start_offset = (seg[0] - md.pos) % sim.config.soup_size
        seg_len = seg[1]

        # Insert by shifting and duplicating (within bounds)
        insert_at = random.randint(0, md.size - 1)
        shift_len = min(seg_len, md.size - insert_at - 1)
        if shift_len <= 0:
            return

        # Shift tail forward
        for i in range(md.size - 1, insert_at + shift_len - 1, -1):
            src = (md.pos + i - shift_len) % sim.config.soup_size
            dst = (md.pos + i) % sim.config.soup_size
            sim.soup.write(dst, sim.soup.read(src))

        # Copy segment into gap
        for i in range(shift_len):
            src = (seg[0] + i) % sim.config.soup_size
            dst = (md.pos + insert_at + i) % sim.config.soup_size
            sim.soup.write(dst, sim.soup.read(src))
        cell.d.mutations += 1

    def _deletion_seg(self, cell: "Cell", sim: "Simulation") -> None:
        """Segment deletion: remove a random NOP-bounded segment from daughter."""
        if self.config.gen_per_del_seg <= 0:
            return
        rate = 1.0 / self.config.gen_per_del_seg
        if random.random() >= rate:
            return

        md = cell.md
        segs = self._find_segments(md.pos, md.size, sim)
        if not segs:
            return

        seg = random.choice(segs)
        seg_start_offset = (seg[0] - md.pos) % sim.config.soup_size
        seg_len = seg[1]

        remaining = md.size - seg_start_offset - seg_len
        if remaining <= 0 or md.size - seg_len < self.config.min_cell_size:
            return

        # Shift everything after segment backward
        for i in range(remaining):
            src = (md.pos + seg_start_offset + seg_len + i) % sim.config.soup_size
            dst = (md.pos + seg_start_offset + i) % sim.config.soup_size
            sim.soup.write(dst, sim.soup.read(src))

        # Fill freed tail with nop0
        for i in range(seg_len):
            addr = (md.pos + md.size - seg_len + i) % sim.config.soup_size
            sim.soup.write(addr, 0)
        cell.d.mutations += 1

    def _find_segments(self, pos: int, size: int, sim: "Simulation") -> list[tuple[int, int]]:
        """Find NOP-bounded segments in a genome region.

        Returns list of (start_addr, length) for each segment.
        Segments are runs of non-NOP instructions bounded by NOP sequences.
        """
        segments = []
        i = 0
        soup = sim.soup
        soup_size = sim.config.soup_size

        while i < size:
            addr = (pos + i) % soup_size
            # Skip NOPs
            if soup.read(addr) in (NOP0, NOP1):
                i += 1
                continue
            # Found start of a segment
            seg_start = addr
            seg_len = 0
            while i < size:
                a = (pos + i) % soup_size
                if soup.read(a) in (NOP0, NOP1):
                    break
                seg_len += 1
                i += 1
            if seg_len > 0:
                segments.append((seg_start, seg_len))

        return segments

    def _find_same_size_mate(self, cell: "Cell", sim: "Simulation") -> "Cell | None":
        """Find a random cell of the same size as cell's daughter."""
        md = cell.md
        if md is None:
            return None
        candidates = [
            c for c in sim.scheduler.queue
            if c is not cell and c.mm.size == md.size
        ]
        if not candidates:
            return None
        return random.choice(candidates)
