"""Read/write Tierra .tie genome files."""

from pathlib import Path
from typing import Optional

# Instruction name to opcode mapping (from opcode0.map)
NAME_TO_OPCODE = {
    "nop0": 0,
    "nop1": 1,
    "not0": 2,
    "shl": 3,
    "zero": 4,
    "ifz": 5,
    "subCAB": 6,
    "subAAC": 7,
    "incA": 8,
    "incB": 9,
    "decC": 10,
    "incC": 11,
    "pushA": 12,
    "pushB": 13,
    "pushC": 14,
    "pushD": 15,
    "popA": 16,
    "popB": 17,
    "popC": 18,
    "popD": 19,
    "jmpo": 20,
    "jmpb": 21,
    "call": 22,
    "ret": 23,
    "movDC": 24,
    "movBA": 25,
    "movii": 26,
    "adro": 27,
    "adrb": 28,
    "adrf": 29,
    "mal": 30,
    "divide": 31,
}

OPCODE_TO_NAME = {v: k for k, v in NAME_TO_OPCODE.items()}

NUM_INSTRUCTIONS = 32


def load_genome(path: str) -> bytes:
    """Load a .tie genome file and return the opcodes as bytes."""
    p = Path(path)
    text = p.read_text()

    opcodes = []
    in_code = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "CODE":
            in_code = True
            continue
        if not in_code:
            continue
        if not stripped or stripped.startswith(";") or stripped.startswith("track"):
            continue

        # Extract instruction mnemonic (first word before ; comment)
        parts = stripped.split(";")[0].strip().split()
        if not parts:
            continue
        mnemonic = parts[0]
        if mnemonic in NAME_TO_OPCODE:
            opcodes.append(NAME_TO_OPCODE[mnemonic])

    return bytes(opcodes)


def save_genome(path: str, genome: bytes, name: str = "unknown",
                parent: str = "unknown") -> None:
    """Save a genome to .tie format."""
    p = Path(path)
    lines = []
    lines.append("")
    lines.append(f"format: 3  bits: 0")
    lines.append(f"genotype: {name}  parent genotype: {parent}")
    lines.append("")
    lines.append("CODE")
    lines.append("")
    lines.append("track 0:")
    lines.append("")
    for i, opcode in enumerate(genome):
        mnemonic = OPCODE_TO_NAME.get(opcode % NUM_INSTRUCTIONS, f"unk{opcode}")
        lines.append(f"{mnemonic}    ; {i:3d}")
    lines.append("")
    p.write_text("\n".join(lines))


def find_genome_file(name: str, search_paths: Optional[list[str]] = None) -> Optional[str]:
    """Find a genome .tie file by genotype name."""
    if search_paths is None:
        search_paths = ["."]
    for sp in search_paths:
        p = Path(sp) / f"{name}.tie"
        if p.exists():
            return str(p)
    return None
