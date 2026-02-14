"""Main loop orchestration (the 'life()' function)."""

import random
import time
from pathlib import Path
from typing import Optional

from .config import Config
from .soup import Soup
from .cpu import CPU
from .cell import Cell, MemRegion
from .scheduler import Scheduler
from .reaper import Reaper
from .genebank import GeneBank
from .mutations import Mutations
from .events import EventBus
from .datalog import DataCollector
from .instructions import INSTRUCTIONS
from .genome_io import load_genome, save_genome


class Simulation:
    def __init__(self, config: Optional[Config] = None, config_path: Optional[str] = None):
        if config is not None:
            self.config = config
        elif config_path is not None:
            self.config = Config.load(config_path)
        else:
            self.config = Config()

        if self.config.seed != 0:
            random.seed(self.config.seed)

        self.soup = Soup(self.config.soup_size)
        self.scheduler = Scheduler(config=self.config)
        self.reaper: Optional[Reaper] = Reaper(self.config)
        self.genebank: Optional[GeneBank] = GeneBank()
        self.mutations: Optional[Mutations] = Mutations(self.config)
        self.events = EventBus()
        self.data_collector = DataCollector()
        self.inst_executed: int = 0
        self.last_repro_inst: int = 0  # for drop_dead check
        self._slicer_cycles: int = 0

        # Disturbance tracking
        self._next_disturbance_inst: int = 0

        # Disk genebank tracking
        self._last_save_inst: int = 0

        # Stats
        self._last_report_inst: int = 0
        self._start_time: float = 0.0

    def boot(self, ancestor_path: str) -> None:
        """Load ancestor organism into center of soup, create first cell."""
        genome = load_genome(ancestor_path)
        pos = self.config.soup_size // 2 - len(genome) // 2
        self.soup.write_block(pos, genome)
        self.soup.allocate_at(pos, len(genome))

        cell = Cell(pos, len(genome))
        cell.cpu.ip = pos
        cell.d.parent_genotype = "0666god"
        cell.d.birth_time = 0

        self.scheduler.add(cell)
        self.soup.add_owner(cell)
        if self.reaper is not None:
            self.reaper.add(cell)
        if self.genebank is not None:
            self.genebank.register(cell, self.soup)

        # Initial mutation rate calculation
        if self.mutations is not None:
            self.mutations.update_rates(len(genome), 1)

        # Schedule first disturbance
        self._schedule_next_disturbance(len(genome))

    def boot_from_config(self, genebank_dir: str) -> None:
        """Boot using inoculation list from config file."""
        if not self.config.inoculations:
            return

        position_mode = None
        for entry in self.config.inoculations:
            entry = entry.strip()
            if entry in ("center", "random"):
                position_mode = entry
                continue
            # It's a genome name
            genome_path = str(Path(genebank_dir) / f"{entry}.tie")
            if not Path(genome_path).exists():
                continue

            genome = load_genome(genome_path)
            if position_mode == "center":
                pos = self.config.soup_size // 2 - len(genome) // 2
            else:
                pos = random.randint(0, self.config.soup_size - len(genome))

            self.soup.write_block(pos, genome)
            self.soup.allocate_at(pos, len(genome))

            cell = Cell(pos, len(genome))
            cell.cpu.ip = pos
            cell.d.parent_genotype = "0666god"
            cell.d.birth_time = 0

            self.scheduler.add(cell)
            self.soup.add_owner(cell)
            if self.reaper is not None:
                self.reaper.add(cell)
            if self.genebank is not None:
                self.genebank.register(cell, self.soup)

        if self.mutations is not None and self.scheduler.num_cells > 0:
            avg_size = sum(c.mm.size for c in self.scheduler.queue) // self.scheduler.num_cells
            self.mutations.update_rates(avg_size, self.scheduler.num_cells)
            self._schedule_next_disturbance(avg_size)

    def run(self, max_instructions: int = 0, report_interval: int = 1_000_000) -> None:
        """Main loop — run until max_instructions or forever."""
        self._start_time = time.time()
        self._last_report_inst = 0

        while max_instructions == 0 or self.inst_executed < max_instructions:
            cell = self.scheduler.current()
            if cell is None:
                break
            self.run_slice(cell)
            self.scheduler.advance()
            self._slicer_cycles += 1

            # Data collection
            if self.data_collector.should_sample(self.inst_executed):
                self.data_collector.sample(self)

            # Periodic bookkeeping
            if self.inst_executed - self._last_report_inst >= report_interval:
                self._periodic_bookkeeping()
                self._last_report_inst = self.inst_executed

                # Check drop_dead
                if self.config.drop_dead > 0:
                    dead_threshold = self.config.drop_dead * 1_000_000
                    if self.inst_executed - self.last_repro_inst > dead_threshold:
                        break

    def run_slice(self, cell: Cell) -> None:
        """Execute one time slice for a cell."""
        slice_size = self.scheduler.compute_slice_size(cell)

        for _ in range(slice_size):
            if not cell.alive:
                break

            # Memory protection: execute check
            if not self.soup.check_execute(cell.cpu.ip, cell, self.config):
                cell.cpu.flag_e = True
                cell.cpu.ip = (cell.cpu.ip + 1) % self.config.soup_size
                cell.d.inst_executed += 1
                cell.d.rep_inst += 1
                self.inst_executed += 1
                continue

            opcode = self.soup.read(cell.cpu.ip) % 32
            cell.cpu._ip_modified = False

            name, execute_fn = INSTRUCTIONS[opcode]
            execute_fn(self, cell)

            if not cell.cpu._ip_modified:
                cell.cpu.ip = (cell.cpu.ip + 1) % self.config.soup_size

            cell.d.inst_executed += 1
            cell.d.rep_inst += 1
            self.inst_executed += 1

            # Background mutation check
            if self.config.rate_mut > 0 and random.random() < self.config.rate_mut:
                if self.mutations is not None:
                    self.mutations.background_mutation(self)

            # Disturbance check
            if self._next_disturbance_inst > 0 and self.inst_executed >= self._next_disturbance_inst:
                self._do_disturbance()

        # Lazy check — only at end of slice, not per-instruction
        if self.reaper is not None:
            self.reaper.check_lazy(cell, self)

    def _do_disturbance(self) -> None:
        """Apply disturbance if configured."""
        if self.reaper is not None and self.config.dist_freq != 0:
            killed = self.reaper.disturbance(self)
            avg_size = 80
            if self.scheduler.num_cells > 0:
                avg_size = sum(c.mm.size for c in self.scheduler.queue) // self.scheduler.num_cells
            self._schedule_next_disturbance(avg_size)

    def _schedule_next_disturbance(self, avg_size: int) -> None:
        """Calculate when the next disturbance should occur."""
        if self.config.dist_freq == 0 or avg_size <= 0:
            self._next_disturbance_inst = 0
            return

        freq = self.config.dist_freq
        if freq < 0:
            # Negative = factor of recovery time
            # Recovery time ~ soup_size / avg_size * avg_size (one generation)
            recovery = self.config.soup_size
            interval = int(abs(freq) * recovery)
        else:
            interval = int(freq * avg_size)

        if interval <= 0:
            self._next_disturbance_inst = 0
        else:
            self._next_disturbance_inst = self.inst_executed + interval

    def _periodic_bookkeeping(self) -> None:
        """Update rates, save genotypes to disk."""
        if self.mutations is not None and self.scheduler.num_cells > 0:
            avg_size = sum(c.mm.size for c in self.scheduler.queue) // self.scheduler.num_cells
            self.mutations.update_rates(avg_size, self.scheduler.num_cells)

        # Disk genebank: periodic save of qualifying genotypes
        self._save_genotypes_to_disk()

    def _save_genotypes_to_disk(self) -> None:
        """Save qualifying genotypes to disk if conditions met."""
        if self.genebank is None or not self.config.disk_bank:
            return
        if self.config.save_freq <= 0:
            return

        save_threshold_inst = self.config.save_freq * 1_000_000
        if self.inst_executed - self._last_save_inst < save_threshold_inst:
            return

        self._last_save_inst = self.inst_executed
        num_cells = self.scheduler.num_cells
        if num_cells == 0:
            return

        save_dir = Path(self.config.genebank_path)
        save_dir.mkdir(parents=True, exist_ok=True)

        for gt in self.genebank.genotypes.values():
            if gt.population <= 0:
                continue
            # Check thresholds
            meets_num = gt.population >= self.config.sav_min_num
            meets_mem = (gt.population * len(gt.genome)) / self.config.soup_size >= self.config.sav_thr_mem
            meets_pop = gt.population / num_cells >= self.config.sav_thr_pop
            if meets_num or meets_mem or meets_pop:
                filepath = save_dir / f"{gt.name}.tie"
                if not filepath.exists():
                    save_genome(str(filepath), gt.genome, gt.name, gt.parent)

    def report(self) -> str:
        """Generate a status report string."""
        elapsed = time.time() - self._start_time if self._start_time else 0
        speed = self.inst_executed / elapsed if elapsed > 0 else 0
        num_genotypes = self.genebank.num_genotypes() if self.genebank else 0
        avg_size = 0
        if self.scheduler.num_cells > 0:
            avg_size = sum(c.mm.size for c in self.scheduler.queue) // self.scheduler.num_cells
        free_pct = self.soup.total_free() / self.soup.size * 100

        return (
            f"InstExe: {self.inst_executed:,}  "
            f"Cells: {self.scheduler.num_cells}  "
            f"Genotypes: {num_genotypes}  "
            f"AvgSize: {avg_size}  "
            f"Free: {free_pct:.1f}%  "
            f"Speed: {speed:,.0f} inst/s"
        )
