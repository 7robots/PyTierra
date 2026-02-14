"""Genotype tracking, hashing, persistence."""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .cell import Cell
    from .soup import Soup


@dataclass
class Genotype:
    name: str
    genome: bytes
    population: int = 0
    origin_time: int = 0
    max_pop: int = 0
    parent: str = ""


@dataclass
class SizeClass:
    genotypes: dict[int, Genotype] = field(default_factory=dict)
    next_label: int = 0  # counter for generating aaa, aab, ...

    def next_name(self, size: int) -> str:
        """Generate next genotype name like '0080aab'."""
        label = self._int_to_label(self.next_label)
        self.next_label += 1
        return f"{size:04d}{label}"

    @staticmethod
    def _int_to_label(n: int) -> str:
        """Convert integer to 3-letter label: 0->aaa, 1->aab, ..., 25->aaz, 26->aba."""
        c3 = chr(ord('a') + (n % 26))
        n //= 26
        c2 = chr(ord('a') + (n % 26))
        n //= 26
        c1 = chr(ord('a') + (n % 26))
        return c1 + c2 + c3


class GeneBank:
    def __init__(self):
        self.size_classes: dict[int, SizeClass] = {}
        self.genotypes: dict[str, Genotype] = {}  # name -> Genotype

    def register(self, cell: "Cell", soup: "Soup") -> Genotype:
        """Register a cell's genome, returning its genotype."""
        genome = soup.read_block(cell.mm.pos, cell.mm.size)
        size = cell.mm.size
        ghash = self._genome_hash(genome)

        if size not in self.size_classes:
            self.size_classes[size] = SizeClass()
        sc = self.size_classes[size]

        if ghash in sc.genotypes:
            gt = sc.genotypes[ghash]
        else:
            name = sc.next_name(size)
            gt = Genotype(
                name=name,
                genome=genome,
                origin_time=0,
                parent=cell.d.parent_genotype,
            )
            sc.genotypes[ghash] = gt
            self.genotypes[name] = gt

        gt.population += 1
        gt.max_pop = max(gt.max_pop, gt.population)
        cell.d.genotype = gt.name
        return gt

    def unregister(self, cell: "Cell") -> None:
        """Decrement population count for cell's genotype."""
        name = cell.d.genotype
        if name in self.genotypes:
            gt = self.genotypes[name]
            gt.population = max(0, gt.population - 1)

    @staticmethod
    def _genome_hash(data: bytes) -> int:
        """Hash a genome for genotype identification."""
        h = 0
        for i, b in enumerate(data):
            h = (h + b * (i + 1)) & 0xFFFFFFFF
        h ^= len(data)
        return h

    def num_genotypes(self) -> int:
        """Return number of genotypes with population > 0."""
        return sum(1 for gt in self.genotypes.values() if gt.population > 0)

    def summary(self) -> dict[str, int]:
        """Return {genotype_name: population} for all living genotypes."""
        return {gt.name: gt.population for gt in self.genotypes.values() if gt.population > 0}
