"""Configuration loading and defaults for PyTierra."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    # Soup
    soup_size: int = 60000

    # Slicing
    slice_size: int = 25
    siz_dep_slice: int = 0
    slice_pow: float = 1.0
    slice_style: int = 2
    slic_fix_frac: float = 0.0
    slic_ran_frac: float = 2.0

    # Mutations
    gen_per_bkg_mut: int = 32
    gen_per_flaw: int = 32
    gen_per_mov_mut: int = 0
    gen_per_div_mut: int = 32
    gen_per_cro_ins_sam_siz: int = 32
    gen_per_ins_ins: int = 32
    gen_per_del_ins: int = 32
    gen_per_cro_ins: int = 32
    gen_per_del_seg: int = 32
    gen_per_ins_seg: int = 32
    gen_per_cro_seg: int = 32
    mut_bit_prop: float = 0.2

    # Memory allocation
    mal_mode: int = 1
    mal_reap_tol: int = 1
    mal_tol: int = 20
    max_free_blocks: int = 800
    mal_sam_siz: int = 0

    # Cell constraints
    min_cell_size: int = 12
    min_gen_mem_siz: int = 12
    min_templ_size: int = 1
    mov_prop_thr_div: float = 0.7

    # Search
    search_limit: int = 5

    # Reaper
    reap_rnd_prop: float = 0.3
    lazy_tol: int = 10
    drop_dead: int = 5

    # Division constraints
    div_same_gen: int = 0
    div_same_siz: int = 0

    # Population
    num_cells: int = 2

    # Disturbance
    dist_freq: float = -0.3
    dist_prop: float = 0.2
    eject_rate: int = 0

    # Memory protection: bit flags — 1=execute, 2=write, 4=read
    mem_mode_free: int = 0   # rwx for free memory (0 = no protection)
    mem_mode_mine: int = 0   # rwx for memory owned by this creature
    mem_mode_prot: int = 2   # rwx for memory owned by another creature (2=write-protect)

    # Genebank
    disk_bank: int = 1
    gene_bnker: int = 0
    genebank_path: str = "gb0/"
    save_freq: int = 100          # frequency of saving (in millions of instructions)
    sav_min_num: int = 10         # minimum population to save genotype
    sav_thr_mem: float = 0.02     # threshold memory occupancy to save
    sav_thr_pop: float = 0.02     # threshold population proportion to save

    # Misc
    alive: int = 0
    new_soup: int = 1
    seed: int = 0
    debug: int = 0

    # Computed rates (set during boot based on population stats)
    rate_mut: float = 0.0
    rate_flaw: float = 0.0
    rate_mov_mut: float = 0.0

    # Inoculation list: [(position_mode, genome_name), ...]
    inoculations: list = field(default_factory=list)

    @classmethod
    def load(cls, path: str) -> "Config":
        """Load config from a Tierra si0-format file."""
        config = cls()
        p = Path(path)
        if not p.exists():
            return config

        text = p.read_text()
        reading_inoc = False
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Inoculation entries come after all key=value pairs
            # They are bare lines like "center" or "0080aaa"
            if "=" not in line and not reading_inoc:
                reading_inoc = True
            if reading_inoc:
                config.inoculations.append(line)
                continue

            # Strip inline comments
            if "#" in line:
                line = line[: line.index("#")].strip()

            if "=" not in line:
                continue

            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()

            attr = _si0_key_to_attr(key)
            if hasattr(config, attr):
                field_type = type(getattr(config, attr))
                try:
                    if field_type is int:
                        setattr(config, attr, int(val))
                    elif field_type is float:
                        setattr(config, attr, float(val))
                    elif field_type is str:
                        setattr(config, attr, val)
                except ValueError:
                    pass

        return config


def _si0_key_to_attr(key: str) -> str:
    """Convert Tierra si0 config key names to Python attribute names."""
    mapping = {
        "SoupSize": "soup_size",
        "SliceSize": "slice_size",
        "SizDepSlice": "siz_dep_slice",
        "SlicePow": "slice_pow",
        "SliceStyle": "slice_style",
        "SlicFixFrac": "slic_fix_frac",
        "SlicRanFrac": "slic_ran_frac",
        "GenPerBkgMut": "gen_per_bkg_mut",
        "GenPerFlaw": "gen_per_flaw",
        "GenPerMovMut": "gen_per_mov_mut",
        "GenPerDivMut": "gen_per_div_mut",
        "GenPerCroInsSamSiz": "gen_per_cro_ins_sam_siz",
        "GenPerInsIns": "gen_per_ins_ins",
        "GenPerDelIns": "gen_per_del_ins",
        "GenPerCroIns": "gen_per_cro_ins",
        "GenPerDelSeg": "gen_per_del_seg",
        "GenPerInsSeg": "gen_per_ins_seg",
        "GenPerCroSeg": "gen_per_cro_seg",
        "MutBitProp": "mut_bit_prop",
        "MalMode": "mal_mode",
        "MalReapTol": "mal_reap_tol",
        "MalTol": "mal_tol",
        "MaxFreeBlocks": "max_free_blocks",
        "MalSamSiz": "mal_sam_siz",
        "MinCellSize": "min_cell_size",
        "MinGenMemSiz": "min_gen_mem_siz",
        "MinTemplSize": "min_templ_size",
        "MovPropThrDiv": "mov_prop_thr_div",
        "SearchLimit": "search_limit",
        "ReapRndProp": "reap_rnd_prop",
        "LazyTol": "lazy_tol",
        "DropDead": "drop_dead",
        "DivSameGen": "div_same_gen",
        "DivSameSiz": "div_same_siz",
        "NumCells": "num_cells",
        "DistFreq": "dist_freq",
        "DistProp": "dist_prop",
        "EjectRate": "eject_rate",
        "MemModeFree": "mem_mode_free",
        "MemModeMine": "mem_mode_mine",
        "MemModeProt": "mem_mode_prot",
        "DiskBank": "disk_bank",
        "GeneBnker": "gene_bnker",
        "GenebankPath": "genebank_path",
        "SaveFreq": "save_freq",
        "SavMinNum": "sav_min_num",
        "SavThrMem": "sav_thr_mem",
        "SavThrPop": "sav_thr_pop",
        "alive": "alive",
        "new_soup": "new_soup",
        "seed": "seed",
        "debug": "debug",
    }
    return mapping.get(key, key.lower())
