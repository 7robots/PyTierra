"""Thread-safe simulation controller API for GUI integration."""

import threading
import time
from dataclasses import dataclass
from typing import Optional, Callable, Any

from .config import Config
from .simulation import Simulation
from .datalog import DataCollector

import numpy as np


@dataclass(frozen=True)
class CellSnapshot:
    """Immutable snapshot of a cell's state."""
    cell_id: int
    pos: int
    size: int
    ip: int
    ax: int
    bx: int
    cx: int
    dx: int
    sp: int
    stack: tuple[int, ...]
    flag_e: bool
    flag_s: bool
    flag_z: bool
    genotype: str
    parent_genotype: str
    fecundity: int
    inst_executed: int
    mutations: int
    alive: bool
    daughter_pos: Optional[int] = None
    daughter_size: Optional[int] = None


@dataclass(frozen=True)
class GenotypeSnapshot:
    """Immutable snapshot of a genotype."""
    name: str
    genome: bytes
    population: int
    max_pop: int
    parent: str
    origin_time: int


class SimulationController:
    """Thread-safe wrapper around Simulation.

    Runs the simulation on a background thread and provides
    a safe API for querying/controlling from the GUI thread.
    """

    def __init__(self, sim: Optional[Simulation] = None):
        self._sim: Optional[Simulation] = sim
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._running = threading.Event()
        self._stop_flag = threading.Event()
        self._slices_per_tick: int = 100
        self._tick_callbacks: list[Callable[[], None]] = []

        self.data_collector = DataCollector()

    @property
    def simulation(self) -> Optional[Simulation]:
        return self._sim

    def set_simulation(self, sim: Simulation) -> None:
        was_running = self._running.is_set()
        if was_running:
            self.pause()
        with self._lock:
            self._sim = sim
        if was_running:
            self.start()

    def start(self) -> None:
        """Start or resume the simulation on a background thread."""
        if self._sim is None:
            return
        if self._thread is not None and self._thread.is_alive():
            self._running.set()
            return

        self._stop_flag.clear()
        self._running.set()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def pause(self) -> None:
        """Pause the simulation (thread stays alive but idle)."""
        self._running.clear()

    def stop(self) -> None:
        """Stop the simulation thread entirely."""
        self._stop_flag.set()
        self._running.set()  # unblock if paused
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def step(self, n: int = 1) -> None:
        """Execute n slices synchronously (for single-stepping)."""
        if self._sim is None:
            return
        with self._lock:
            for _ in range(n):
                cell = self._sim.scheduler.current()
                if cell is None:
                    break
                self._sim.run_slice(cell)
                self._sim.scheduler.advance()
            self._maybe_collect_data()

    def set_speed(self, slices_per_tick: int) -> None:
        """Set how many slices run per tick."""
        self._slices_per_tick = max(1, slices_per_tick)

    def on_tick(self, callback: Callable[[], None]) -> None:
        """Register a callback to be called after each batch of slices."""
        self._tick_callbacks.append(callback)

    def get_cell(self, cell_id: int) -> Optional[CellSnapshot]:
        """Get an immutable snapshot of a cell."""
        with self._lock:
            if self._sim is None:
                return None
            for cell in self._sim.scheduler.queue:
                if cell._id == cell_id:
                    return self._snapshot_cell(cell)
        return None

    def get_cell_at(self, addr: int) -> Optional[CellSnapshot]:
        """Get the cell that owns the given soup address."""
        with self._lock:
            if self._sim is None:
                return None
            cell = self._sim.soup.owner_at(addr)
            if cell is not None:
                return self._snapshot_cell(cell)
        return None

    def get_all_cells(self) -> list[CellSnapshot]:
        """Get snapshots of all living cells."""
        with self._lock:
            if self._sim is None:
                return []
            return [self._snapshot_cell(c) for c in self._sim.scheduler.queue]

    def get_genotype(self, name: str) -> Optional[GenotypeSnapshot]:
        """Get a genotype snapshot."""
        with self._lock:
            if self._sim is None or self._sim.genebank is None:
                return None
            if name in self._sim.genebank.genotypes:
                gt = self._sim.genebank.genotypes[name]
                return GenotypeSnapshot(
                    name=gt.name, genome=gt.genome, population=gt.population,
                    max_pop=gt.max_pop, parent=gt.parent, origin_time=gt.origin_time,
                )
        return None

    def read_soup(self, addr: int, count: int) -> bytes:
        """Read raw soup bytes for disassembly view."""
        with self._lock:
            if self._sim is None:
                return b""
            return self._sim.soup.read_block(addr, count)

    def get_all_genotypes(self) -> list[GenotypeSnapshot]:
        """Return snapshots of all living genotypes (population > 0)."""
        with self._lock:
            if self._sim is None or self._sim.genebank is None:
                return []
            result = []
            for gt in self._sim.genebank.genotypes.values():
                if gt.population > 0:
                    result.append(GenotypeSnapshot(
                        name=gt.name, genome=gt.genome,
                        population=gt.population, max_pop=gt.max_pop,
                        parent=gt.parent, origin_time=gt.origin_time,
                    ))
            return result

    def get_soup_image(self, width: int = 512) -> np.ndarray:
        """Render the soup as an RGBA numpy array.

        Returns array of shape (height, width, 4) where each pixel
        represents one instruction colored by opcode.
        """
        with self._lock:
            if self._sim is None:
                return np.zeros((1, width, 4), dtype=np.uint8)
            return self._render_soup(width)

    def inject_genome(self, genome: bytes, position: int) -> bool:
        """Add a creature at the given position."""
        with self._lock:
            if self._sim is None:
                return False
            from .cell import Cell
            size = len(genome)
            result = self._sim.soup.allocate_at(position, size)
            if not result:
                return False
            self._sim.soup.write_block(position, genome)
            cell = Cell(position, size)
            cell.cpu.ip = position
            cell.d.parent_genotype = "injected"
            cell.d.birth_time = self._sim.inst_executed
            self._sim.scheduler.add(cell)
            self._sim.soup.add_owner(cell)
            if self._sim.reaper is not None:
                self._sim.reaper.add(cell)
            if self._sim.genebank is not None:
                self._sim.genebank.register(cell, self._sim.soup)
            return True

    def update_config(self, **kwargs: Any) -> None:
        """Update config parameters on the running simulation."""
        with self._lock:
            if self._sim is None:
                return
            for key, value in kwargs.items():
                if hasattr(self._sim.config, key):
                    setattr(self._sim.config, key, value)

    @property
    def inst_executed(self) -> int:
        if self._sim is None:
            return 0
        return self._sim.inst_executed

    @property
    def is_running(self) -> bool:
        return self._running.is_set() and not self._stop_flag.is_set()

    def _run_loop(self) -> None:
        """Background thread main loop."""
        while not self._stop_flag.is_set():
            self._running.wait()
            if self._stop_flag.is_set():
                break

            with self._lock:
                if self._sim is None:
                    break
                for _ in range(self._slices_per_tick):
                    cell = self._sim.scheduler.current()
                    if cell is None:
                        self._running.clear()
                        break
                    self._sim.run_slice(cell)
                    self._sim.scheduler.advance()
                self._maybe_collect_data()
                self._sim._periodic_bookkeeping()

            # Notify tick callbacks (outside lock)
            for cb in self._tick_callbacks:
                cb()

            # Small sleep to not starve the GUI thread
            time.sleep(0.001)

    def _maybe_collect_data(self) -> None:
        """Collect data if enough instructions have passed."""
        if self._sim is not None and self.data_collector.should_sample(self._sim.inst_executed):
            self.data_collector.sample(self._sim)

    @staticmethod
    def _snapshot_cell(cell) -> CellSnapshot:
        return CellSnapshot(
            cell_id=cell._id,
            pos=cell.mm.pos,
            size=cell.mm.size,
            ip=cell.cpu.ip,
            ax=cell.cpu.ax,
            bx=cell.cpu.bx,
            cx=cell.cpu.cx,
            dx=cell.cpu.dx,
            sp=cell.cpu.sp,
            stack=tuple(cell.cpu.stack),
            flag_e=cell.cpu.flag_e,
            flag_s=cell.cpu.flag_s,
            flag_z=cell.cpu.flag_z,
            genotype=cell.d.genotype,
            parent_genotype=cell.d.parent_genotype,
            fecundity=cell.d.fecundity,
            inst_executed=cell.d.inst_executed,
            mutations=cell.d.mutations,
            alive=cell.alive,
            daughter_pos=cell.md.pos if cell.md else None,
            daughter_size=cell.md.size if cell.md else None,
        )

    def _render_soup(self, width: int) -> np.ndarray:
        """Render soup data to RGBA image array."""
        soup_size = self._sim.config.soup_size
        height = (soup_size + width - 1) // width

        # Pad soup data to full image size
        padded = np.zeros(height * width, dtype=np.uint8)
        padded[:soup_size] = self._sim.soup.data

        # Map opcodes to colors (32 colors for 32 instructions)
        opcodes = padded % 32
        rgba = np.zeros((height * width, 4), dtype=np.uint8)
        rgba[:, 0] = _OPCODE_COLORS[opcodes, 0]
        rgba[:, 1] = _OPCODE_COLORS[opcodes, 1]
        rgba[:, 2] = _OPCODE_COLORS[opcodes, 2]
        rgba[:, 3] = 255

        return rgba.reshape(height, width, 4)


# Opcode color table: 32 colors for visual distinction
_OPCODE_COLORS = np.array([
    # NOPs: blue shades
    [60, 60, 200],    # 0  nop0
    [80, 80, 220],    # 1  nop1
    # Arithmetic: green shades
    [40, 180, 40],    # 2  not0
    [60, 200, 60],    # 3  shl
    [30, 160, 30],    # 4  zero
    [80, 220, 80],    # 5  ifz
    [50, 190, 50],    # 6  subCAB
    [70, 210, 70],    # 7  subAAC
    [45, 175, 45],    # 8  incA
    [55, 185, 55],    # 9  incB
    [35, 165, 35],    # 10 decC
    [65, 195, 65],    # 11 incC
    # Stack: yellow/amber
    [220, 200, 40],   # 12 pushA
    [230, 210, 50],   # 13 pushB
    [210, 190, 30],   # 14 pushC
    [240, 220, 60],   # 15 pushD
    [200, 180, 40],   # 16 popA
    [210, 190, 50],   # 17 popB
    [190, 170, 30],   # 18 popC
    [220, 200, 60],   # 19 popD
    # Control flow: red/orange
    [220, 60, 40],    # 20 jmpo
    [200, 50, 30],    # 21 jmpb
    [240, 80, 50],    # 22 call
    [180, 40, 20],    # 23 ret
    # Moves: purple/magenta
    [180, 60, 200],   # 24 movDC
    [200, 80, 220],   # 25 movBA
    [160, 40, 180],   # 26 movii
    # Address: cyan
    [40, 200, 200],   # 27 adro
    [30, 180, 180],   # 28 adrb
    [50, 210, 210],   # 29 adrf
    # Memory/division: white/bright
    [240, 240, 240],  # 30 mal
    [255, 200, 200],  # 31 divide
], dtype=np.uint8)
