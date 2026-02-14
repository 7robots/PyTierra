"""All 32 instruction implementations for PyTierra."""

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .simulation import Simulation
    from .cell import Cell

NOP0 = 0
NOP1 = 1


def _flaw(sim: "Simulation") -> int:
    """Return 0 most of the time, occasionally ±1."""
    if sim.config.rate_flaw <= 0:
        return 0
    if random.random() < sim.config.rate_flaw:
        return random.choice([-1, 1])
    return 0


def _find_template(sim: "Simulation", ip: int, direction: str) -> tuple[int, int]:
    """Find complementary template starting after ip.

    Args:
        sim: simulation context
        ip: instruction pointer (current instruction)
        direction: 'o' (outward/bidirectional), 'f' (forward), 'b' (backward)

    Returns:
        (address after matched template, template_length) or (-1, template_length)
        template_length is the number of nop instructions in the source template
    """
    soup = sim.soup
    soup_size = sim.config.soup_size

    # Read template: collect consecutive nop0/nop1 starting at ip+1
    template = []
    pos = (ip + 1) % soup_size
    while soup.read(pos) in (NOP0, NOP1):
        template.append(soup.read(pos))
        pos = (pos + 1) % soup_size
        if len(template) >= soup_size:
            break  # safety

    if not template:
        return (-1, 0)

    tlen = len(template)

    # Build complement
    complement = [1 - bit for bit in template]

    # Calculate search limit
    avg_size = _avg_cell_size(sim)
    max_dist = int(sim.config.search_limit * avg_size) if avg_size > 0 else sim.config.soup_size

    def _match_at(start: int) -> bool:
        for j in range(tlen):
            if soup.read((start + j) % soup_size) != complement[j]:
                return False
        return True

    # Search for complement
    if direction == 'f':
        # Forward only: start searching after source template
        search_start = (ip + 1 + tlen) % soup_size
        for dist in range(1, max_dist + 1):
            check = (search_start + dist) % soup_size
            if _match_at(check):
                return ((check + tlen) % soup_size, tlen)
    elif direction == 'b':
        # Backward only
        for dist in range(1, max_dist + 1):
            check = (ip - dist) % soup_size
            if _match_at(check):
                return ((check + tlen) % soup_size, tlen)
    elif direction == 'o':
        # Outward: alternate forward and backward
        search_start = (ip + 1 + tlen) % soup_size
        for dist in range(1, max_dist + 1):
            # Forward
            check_f = (search_start + dist) % soup_size
            if _match_at(check_f):
                return ((check_f + tlen) % soup_size, tlen)
            # Backward
            check_b = (ip - dist) % soup_size
            if _match_at(check_b):
                return ((check_b + tlen) % soup_size, tlen)

    return (-1, tlen)


def _avg_cell_size(sim: "Simulation") -> int:
    """Return average cell size in the population."""
    if not sim.scheduler.queue:
        return 80  # default
    total = sum(c.mm.size for c in sim.scheduler.queue)
    return total // len(sim.scheduler.queue)


def _skip_template(cell: "Cell", soup_size: int, soup) -> None:
    """Advance IP past any nop template following current IP."""
    pos = (cell.cpu.ip + 1) % soup_size
    while soup.read(pos) in (NOP0, NOP1):
        pos = (pos + 1) % soup_size
    # Set IP to the last nop so the main loop increment brings us to pos
    cell.cpu.ip = (pos - 1) % soup_size


# === Instruction implementations ===

def nop(sim: "Simulation", cell: "Cell") -> None:
    """nop0, nop1: No operation."""
    pass


def not0(sim: "Simulation", cell: "Cell") -> None:
    """Flip low bit of cx."""
    cell.cpu.cx ^= (1 + _flaw(sim))
    cell.cpu.set_flags(cell.cpu.cx)


def shl(sim: "Simulation", cell: "Cell") -> None:
    """Shift cx left by 1."""
    cell.cpu.cx <<= (1 + _flaw(sim))
    cell.cpu.set_flags(cell.cpu.cx)


def zero(sim: "Simulation", cell: "Cell") -> None:
    """Zero cx register (movdd with cc operands)."""
    cell.cpu.cx = 0 + _flaw(sim)
    cell.cpu.set_flags(cell.cpu.cx)


def ifz(sim: "Simulation", cell: "Cell") -> None:
    """If cx == 0, execute next instruction; otherwise skip it."""
    if cell.cpu.cx != 0:
        # Skip next instruction
        cell.cpu.ip = (cell.cpu.ip + 1) % sim.config.soup_size


def sub_cab(sim: "Simulation", cell: "Cell") -> None:
    """cx = ax - bx"""
    cell.cpu.cx = cell.cpu.ax - cell.cpu.bx + _flaw(sim)
    cell.cpu.set_flags(cell.cpu.cx)


def sub_aac(sim: "Simulation", cell: "Cell") -> None:
    """ax = ax - cx"""
    cell.cpu.ax = cell.cpu.ax - cell.cpu.cx + _flaw(sim)
    cell.cpu.set_flags(cell.cpu.ax)


def inc_a(sim: "Simulation", cell: "Cell") -> None:
    """Increment ax."""
    cell.cpu.ax += 1 + _flaw(sim)
    cell.cpu.set_flags(cell.cpu.ax)


def inc_b(sim: "Simulation", cell: "Cell") -> None:
    """Increment bx."""
    cell.cpu.bx += 1 + _flaw(sim)
    cell.cpu.set_flags(cell.cpu.bx)


def dec_c(sim: "Simulation", cell: "Cell") -> None:
    """Decrement cx."""
    cell.cpu.cx -= 1 + _flaw(sim)
    cell.cpu.set_flags(cell.cpu.cx)


def inc_c(sim: "Simulation", cell: "Cell") -> None:
    """Increment cx."""
    cell.cpu.cx += 1 + _flaw(sim)
    cell.cpu.set_flags(cell.cpu.cx)


def push_a(sim: "Simulation", cell: "Cell") -> None:
    """Push ax onto stack."""
    cell.cpu.push(cell.cpu.ax + _flaw(sim))


def push_b(sim: "Simulation", cell: "Cell") -> None:
    """Push bx onto stack."""
    cell.cpu.push(cell.cpu.bx + _flaw(sim))


def push_c(sim: "Simulation", cell: "Cell") -> None:
    """Push cx onto stack."""
    cell.cpu.push(cell.cpu.cx + _flaw(sim))


def push_d(sim: "Simulation", cell: "Cell") -> None:
    """Push dx onto stack."""
    cell.cpu.push(cell.cpu.dx + _flaw(sim))


def pop_a(sim: "Simulation", cell: "Cell") -> None:
    """Pop into ax."""
    cell.cpu.ax = cell.cpu.pop() + _flaw(sim)


def pop_b(sim: "Simulation", cell: "Cell") -> None:
    """Pop into bx."""
    cell.cpu.bx = cell.cpu.pop() + _flaw(sim)


def pop_c(sim: "Simulation", cell: "Cell") -> None:
    """Pop into cx."""
    cell.cpu.cx = cell.cpu.pop() + _flaw(sim)


def pop_d(sim: "Simulation", cell: "Cell") -> None:
    """Pop into dx."""
    cell.cpu.dx = cell.cpu.pop() + _flaw(sim)


def jmpo(sim: "Simulation", cell: "Cell") -> None:
    """Jump outward (bidirectional template search)."""
    addr, tlen = _find_template(sim, cell.cpu.ip, 'o')
    if addr >= 0:
        cell.cpu.ip = addr % sim.config.soup_size
        cell.cpu._ip_modified = True
        cell.cpu.flag_e = False
    else:
        cell.cpu.flag_e = True
        if tlen > 0:
            _skip_template(cell, sim.config.soup_size, sim.soup)


def jmpb(sim: "Simulation", cell: "Cell") -> None:
    """Jump backward (backward template search)."""
    addr, tlen = _find_template(sim, cell.cpu.ip, 'b')
    if addr >= 0:
        cell.cpu.ip = addr % sim.config.soup_size
        cell.cpu._ip_modified = True
        cell.cpu.flag_e = False
    else:
        cell.cpu.flag_e = True
        if tlen > 0:
            _skip_template(cell, sim.config.soup_size, sim.soup)


def call(sim: "Simulation", cell: "Cell") -> None:
    """Call: search outward for template, push return address, jump."""
    addr, tlen = _find_template(sim, cell.cpu.ip, 'o')
    if addr >= 0:
        # Push return address (instruction after the template)
        ret_addr = (cell.cpu.ip + 1 + tlen) % sim.config.soup_size
        cell.cpu.push(ret_addr)
        cell.cpu.ip = addr % sim.config.soup_size
        cell.cpu._ip_modified = True
        cell.cpu.flag_e = False
    else:
        cell.cpu.flag_e = True
        if tlen > 0:
            _skip_template(cell, sim.config.soup_size, sim.soup)


def ret(sim: "Simulation", cell: "Cell") -> None:
    """Return: pop address from stack and jump to it."""
    addr = cell.cpu.pop() + _flaw(sim)
    cell.cpu.ip = addr % sim.config.soup_size
    cell.cpu._ip_modified = True


def mov_dc(sim: "Simulation", cell: "Cell") -> None:
    """Move cx to dx."""
    cell.cpu.dx = cell.cpu.cx + _flaw(sim)
    cell.cpu.set_flags(cell.cpu.dx)


def mov_ba(sim: "Simulation", cell: "Cell") -> None:
    """Move ax to bx."""
    cell.cpu.bx = cell.cpu.ax + _flaw(sim)
    cell.cpu.set_flags(cell.cpu.bx)


def movii(sim: "Simulation", cell: "Cell") -> None:
    """Move [bx] to [ax] (copy one instruction). Write only to daughter memory."""
    src_addr = cell.cpu.bx
    dst_addr = cell.cpu.ax

    # Check write permission: dst must be in daughter memory
    if not cell.owns_daughter(dst_addr, sim.config.soup_size):
        cell.cpu.flag_e = True
        return

    # Memory protection: check write access
    if not sim.soup.check_write(dst_addr, cell, sim.config):
        cell.cpu.flag_e = True
        return

    value = sim.soup.read(src_addr)

    # Copy mutation
    if sim.config.rate_mov_mut > 0 and random.random() < sim.config.rate_mov_mut:
        if random.random() < sim.config.mut_bit_prop:
            # Flip a random bit
            value ^= (1 << random.randint(0, 4))
        else:
            # Random instruction
            value = random.randint(0, 31)
        cell.d.mutations += 1

    sim.soup.write(dst_addr, value)
    cell.d.mov_daught += 1

    # Track offset range for division validation
    offset = (dst_addr - cell.md.pos) % sim.config.soup_size
    cell.d.mov_off_min = min(cell.d.mov_off_min, offset)
    cell.d.mov_off_max = max(cell.d.mov_off_max, offset)
    cell.cpu.flag_e = False


def adro(sim: "Simulation", cell: "Cell") -> None:
    """Address outward: find template bidirectionally, result in ax."""
    addr, tlen = _find_template(sim, cell.cpu.ip, 'o')
    if addr >= 0:
        cell.cpu.ax = addr % sim.config.soup_size
        cell.cpu.cx = tlen
        cell.cpu.flag_e = False
    else:
        cell.cpu.flag_e = True
    if tlen > 0:
        _skip_template(cell, sim.config.soup_size, sim.soup)


def adrb(sim: "Simulation", cell: "Cell") -> None:
    """Address backward: find template backward, result in ax."""
    addr, tlen = _find_template(sim, cell.cpu.ip, 'b')
    if addr >= 0:
        cell.cpu.ax = addr % sim.config.soup_size
        cell.cpu.cx = tlen
        cell.cpu.flag_e = False
    else:
        cell.cpu.flag_e = True
    if tlen > 0:
        _skip_template(cell, sim.config.soup_size, sim.soup)


def adrf(sim: "Simulation", cell: "Cell") -> None:
    """Address forward: find template forward, result in ax."""
    addr, tlen = _find_template(sim, cell.cpu.ip, 'f')
    if addr >= 0:
        cell.cpu.ax = addr % sim.config.soup_size
        cell.cpu.cx = tlen
        cell.cpu.flag_e = False
    else:
        cell.cpu.flag_e = True
    if tlen > 0:
        _skip_template(cell, sim.config.soup_size, sim.soup)


def mal(sim: "Simulation", cell: "Cell") -> None:
    """Allocate memory for daughter cell."""
    size = cell.cpu.cx
    if size < sim.config.min_cell_size or size > cell.mm.size * 2:
        cell.cpu.flag_e = True
        return

    # Deallocate existing daughter if present
    if cell.md is not None:
        sim.soup.deallocate(cell.md.pos, cell.md.size)
        cell.md = None

    # Try to allocate
    result = sim.soup.allocate(size, sim.config.mal_mode)
    if result is None:
        # Soup full — reap a cell and retry
        if sim.reaper is not None:
            sim.reaper.reap(sim)
            result = sim.soup.allocate(size, sim.config.mal_mode)

    if result is None:
        cell.cpu.flag_e = True
        return

    from .cell import MemRegion
    addr, actual_size = result
    cell.md = MemRegion(addr, actual_size)
    cell.cpu.ax = addr
    cell.d.mov_off_min = actual_size  # will be reduced by movii
    cell.d.mov_off_max = 0
    cell.d.mov_daught = 0
    cell.cpu.flag_e = False


def divide(sim: "Simulation", cell: "Cell") -> None:
    """Create independent daughter cell from copied memory."""
    md = cell.md
    if md is None:
        cell.cpu.flag_e = True
        return

    # Validate daughter size
    if md.size < sim.config.min_cell_size:
        cell.cpu.flag_e = True
        return

    # Validate copy threshold
    thresh = int(md.size * sim.config.mov_prop_thr_div)
    if cell.d.mov_daught < thresh:
        cell.cpu.flag_e = True
        return

    # Validate same size if required
    if sim.config.div_same_siz and md.size != cell.mm.size:
        cell.cpu.flag_e = True
        return

    # Apply genetic operators to daughter
    if sim.mutations is not None:
        sim.mutations.genetic_ops(cell, sim)

    # Create new cell
    from .cell import Cell as CellClass
    daughter = CellClass(md.pos, md.size)
    daughter.cpu.ip = md.pos
    daughter.d.parent_genotype = cell.d.genotype
    daughter.d.birth_time = sim.inst_executed

    # Register in genebank
    if sim.genebank is not None:
        gt = sim.genebank.register(daughter, sim.soup)
        if gt.population == 1:
            sim.events.emit("NEW_GENOTYPE", genotype=gt)

    # Add to scheduler and reaper
    sim.scheduler.add(daughter)
    sim.soup.add_owner(daughter)
    if sim.reaper is not None:
        sim.reaper.add(daughter)

    # Emit birth event
    sim.events.emit("CELL_BORN", cell=daughter, parent=cell)
    sim.last_repro_inst = sim.inst_executed

    # Reset mother state
    cell.md = None
    cell.d.fecundity += 1
    cell.d.mov_daught = 0
    cell.d.mov_off_min = 0
    cell.d.mov_off_max = 0
    cell.d.rep_inst = 0
    cell.cpu.flag_e = False


# Instruction dispatch table: opcode -> (name, execute_fn)
INSTRUCTIONS = {
    0:  ("nop0",    nop),
    1:  ("nop1",    nop),
    2:  ("not0",    not0),
    3:  ("shl",     shl),
    4:  ("zero",    zero),
    5:  ("ifz",     ifz),
    6:  ("subCAB",  sub_cab),
    7:  ("subAAC",  sub_aac),
    8:  ("incA",    inc_a),
    9:  ("incB",    inc_b),
    10: ("decC",    dec_c),
    11: ("incC",    inc_c),
    12: ("pushA",   push_a),
    13: ("pushB",   push_b),
    14: ("pushC",   push_c),
    15: ("pushD",   push_d),
    16: ("popA",    pop_a),
    17: ("popB",    pop_b),
    18: ("popC",    pop_c),
    19: ("popD",    pop_d),
    20: ("jmpo",    jmpo),
    21: ("jmpb",    jmpb),
    22: ("call",    call),
    23: ("ret",     ret),
    24: ("movDC",   mov_dc),
    25: ("movBA",   mov_ba),
    26: ("movii",   movii),
    27: ("adro",    adro),
    28: ("adrb",    adrb),
    29: ("adrf",    adrf),
    30: ("mal",     mal),
    31: ("divide",  divide),
}
