"""Save/restore simulation state."""

import pickle
import random
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .simulation import Simulation


def save_state(sim: "Simulation", path: str) -> None:
    """Serialize complete simulation state to a file."""
    state = {
        "version": 1,
        "config": sim.config,
        "soup_data": bytes(sim.soup.data),
        "soup_free_blocks": sim.soup.free_blocks,
        "cells": _serialize_cells(sim),
        "scheduler_order": [c._id for c in sim.scheduler.queue],
        "scheduler_idx": sim.scheduler._current_idx,
        "reaper_order": [c._id for c in sim.reaper.queue] if sim.reaper else [],
        "genebank": _serialize_genebank(sim.genebank) if sim.genebank else None,
        "inst_executed": sim.inst_executed,
        "last_repro_inst": sim.last_repro_inst,
        "rng_state": random.getstate(),
    }
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        pickle.dump(state, f, protocol=5)


def load_state(path: str) -> "Simulation":
    """Deserialize a simulation state from a file."""
    from .simulation import Simulation
    from .cell import Cell, MemRegion, Demographics
    from .cpu import CPU
    from .genebank import GeneBank, Genotype, SizeClass

    with open(path, "rb") as f:
        state = pickle.load(f)

    config = state["config"]
    sim = Simulation(config=config)

    # Restore RNG
    random.setstate(state["rng_state"])

    # Restore soup data
    import numpy as np
    sim.soup.data = np.frombuffer(bytearray(state["soup_data"]), dtype=np.uint8).copy()
    sim.soup.free_blocks = state["soup_free_blocks"]

    # Restore cells
    cell_map = {}  # id -> Cell
    for cd in state["cells"]:
        cell = Cell(cd["mm_pos"], cd["mm_size"])
        cell._id = cd["id"]
        cell.alive = cd["alive"]
        cell.ib = cd["ib"]

        # CPU
        cell.cpu.ax = cd["cpu"]["ax"]
        cell.cpu.bx = cd["cpu"]["bx"]
        cell.cpu.cx = cd["cpu"]["cx"]
        cell.cpu.dx = cd["cpu"]["dx"]
        cell.cpu.ip = cd["cpu"]["ip"]
        cell.cpu.sp = cd["cpu"]["sp"]
        cell.cpu.stack = cd["cpu"]["stack"]
        cell.cpu.flag_e = cd["cpu"]["flag_e"]
        cell.cpu.flag_s = cd["cpu"]["flag_s"]
        cell.cpu.flag_z = cd["cpu"]["flag_z"]

        # Demographics
        for k, v in cd["demographics"].items():
            setattr(cell.d, k, v)

        # Daughter memory
        if cd["md_pos"] is not None:
            cell.md = MemRegion(cd["md_pos"], cd["md_size"])

        cell_map[cd["id"]] = cell
        sim.soup.add_owner(cell)

    # Restore scheduler order
    for cid in state["scheduler_order"]:
        if cid in cell_map:
            sim.scheduler.add(cell_map[cid])
    sim.scheduler._current_idx = state["scheduler_idx"]

    # Restore reaper order
    if sim.reaper is not None:
        for cid in state["reaper_order"]:
            if cid in cell_map:
                sim.reaper.add(cell_map[cid])

    # Restore genebank
    if state["genebank"] is not None and sim.genebank is not None:
        gb_data = state["genebank"]
        for sc_data in gb_data["size_classes"]:
            size = sc_data["size"]
            sc = SizeClass()
            sc.next_label = sc_data["next_label"]
            for gt_data in sc_data["genotypes"]:
                gt = Genotype(
                    name=gt_data["name"],
                    genome=gt_data["genome"],
                    population=gt_data["population"],
                    origin_time=gt_data["origin_time"],
                    max_pop=gt_data["max_pop"],
                    parent=gt_data["parent"],
                )
                ghash = GeneBank._genome_hash(gt.genome)
                sc.genotypes[ghash] = gt
                sim.genebank.genotypes[gt.name] = gt
            sim.genebank.size_classes[size] = sc

    # Restore counters
    sim.inst_executed = state["inst_executed"]
    sim.last_repro_inst = state["last_repro_inst"]

    # Update Cell._next_id to avoid conflicts
    if cell_map:
        Cell._next_id = max(c._id for c in cell_map.values()) + 1

    return sim


def _serialize_cells(sim: "Simulation") -> list[dict]:
    """Serialize all cells to dicts."""
    cells = set()
    for c in sim.scheduler.queue:
        cells.add(c)
    if sim.reaper:
        for c in sim.reaper.queue:
            cells.add(c)

    result = []
    for cell in cells:
        cd = {
            "id": cell._id,
            "mm_pos": cell.mm.pos,
            "mm_size": cell.mm.size,
            "md_pos": cell.md.pos if cell.md else None,
            "md_size": cell.md.size if cell.md else None,
            "alive": cell.alive,
            "ib": cell.ib,
            "cpu": {
                "ax": cell.cpu.ax,
                "bx": cell.cpu.bx,
                "cx": cell.cpu.cx,
                "dx": cell.cpu.dx,
                "ip": cell.cpu.ip,
                "sp": cell.cpu.sp,
                "stack": cell.cpu.stack[:],
                "flag_e": cell.cpu.flag_e,
                "flag_s": cell.cpu.flag_s,
                "flag_z": cell.cpu.flag_z,
            },
            "demographics": {
                "genotype": cell.d.genotype,
                "parent_genotype": cell.d.parent_genotype,
                "fecundity": cell.d.fecundity,
                "inst_executed": cell.d.inst_executed,
                "rep_inst": cell.d.rep_inst,
                "mutations": cell.d.mutations,
                "mov_daught": cell.d.mov_daught,
                "mov_off_min": cell.d.mov_off_min,
                "mov_off_max": cell.d.mov_off_max,
                "birth_time": cell.d.birth_time,
            },
        }
        result.append(cd)
    return result


def _serialize_genebank(genebank) -> dict:
    """Serialize genebank to a dict."""
    size_classes = []
    for size, sc in genebank.size_classes.items():
        genotypes = []
        for ghash, gt in sc.genotypes.items():
            genotypes.append({
                "name": gt.name,
                "genome": gt.genome,
                "population": gt.population,
                "origin_time": gt.origin_time,
                "max_pop": gt.max_pop,
                "parent": gt.parent,
            })
        size_classes.append({
            "size": size,
            "next_label": sc.next_label,
            "genotypes": genotypes,
        })
    return {"size_classes": size_classes}
