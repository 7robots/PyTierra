"""Data loggers for time-series collection and histograms."""

from collections import deque
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .simulation import Simulation


@dataclass
class DataPoint:
    time: int  # instruction count
    value: float


class TimeSeriesLog:
    """Ring buffer of (instruction_count, value) data points."""

    def __init__(self, capacity: int = 10_000):
        self.capacity = capacity
        self.data: deque[DataPoint] = deque(maxlen=capacity)

    def record(self, time: int, value: float) -> None:
        self.data.append(DataPoint(time, value))

    def values(self) -> list[float]:
        return [p.value for p in self.data]

    def times(self) -> list[int]:
        return [p.time for p in self.data]

    def last(self) -> Optional[DataPoint]:
        return self.data[-1] if self.data else None

    def clear(self) -> None:
        self.data.clear()

    def __len__(self) -> int:
        return len(self.data)


class DataCollector:
    """Collects simulation statistics into time-series logs."""

    def __init__(self, sample_interval: int = 25_000):
        self.sample_interval = sample_interval
        self._last_sample_inst: int = 0

        # Built-in series
        self.population_size = TimeSeriesLog()
        self.mean_creature_size = TimeSeriesLog()
        self.max_fitness = TimeSeriesLog()
        self.num_genotypes = TimeSeriesLog()
        self.soup_fullness = TimeSeriesLog()
        self.instructions_per_second = TimeSeriesLog()

        # Snapshot data (updated on sample)
        self.size_histogram: dict[int, int] = {}
        self.genotype_frequency: dict[str, int] = {}

        self._last_speed_inst: int = 0
        self._last_speed_time: float = 0.0

    def should_sample(self, inst_executed: int) -> bool:
        """Check if it's time to collect a sample."""
        return inst_executed - self._last_sample_inst >= self.sample_interval

    def sample(self, sim: "Simulation") -> None:
        """Collect all data series from the simulation."""
        import time

        t = sim.inst_executed
        self._last_sample_inst = t

        # Population size
        num_cells = sim.scheduler.num_cells
        self.population_size.record(t, num_cells)

        # Mean creature size
        if num_cells > 0:
            avg_size = sum(c.mm.size for c in sim.scheduler.queue) / num_cells
            self.mean_creature_size.record(t, avg_size)
        else:
            self.mean_creature_size.record(t, 0)

        # Max fitness (highest fecundity)
        if num_cells > 0:
            max_fec = max(c.d.fecundity for c in sim.scheduler.queue)
            self.max_fitness.record(t, max_fec)
        else:
            self.max_fitness.record(t, 0)

        # Genotype count
        if sim.genebank is not None:
            self.num_genotypes.record(t, sim.genebank.num_genotypes())
        else:
            self.num_genotypes.record(t, 0)

        # Soup fullness
        fullness = 100.0 * (1.0 - sim.soup.total_free() / sim.soup.size)
        self.soup_fullness.record(t, fullness)

        # Instructions per second
        now = time.time()
        if self._last_speed_time > 0:
            dt = now - self._last_speed_time
            if dt > 0:
                speed = (t - self._last_speed_inst) / dt
                self.instructions_per_second.record(t, speed)
        self._last_speed_inst = t
        self._last_speed_time = now

        # Size histogram snapshot
        self.size_histogram.clear()
        for cell in sim.scheduler.queue:
            sz = cell.mm.size
            self.size_histogram[sz] = self.size_histogram.get(sz, 0) + 1

        # Genotype frequency snapshot
        if sim.genebank is not None:
            self.genotype_frequency = sim.genebank.summary()
        else:
            self.genotype_frequency = {}

    def all_series(self) -> dict[str, TimeSeriesLog]:
        """Return all time-series logs by name."""
        return {
            "population_size": self.population_size,
            "mean_creature_size": self.mean_creature_size,
            "max_fitness": self.max_fitness,
            "num_genotypes": self.num_genotypes,
            "soup_fullness": self.soup_fullness,
            "instructions_per_second": self.instructions_per_second,
        }
