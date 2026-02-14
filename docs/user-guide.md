# User Guide

## Installation

### Prerequisites

- Python 3.10 or later
- For GUI: a display server (X11 on Linux, native on macOS/Windows)

### Install with uv

```bash
git clone https://github.com/7robots/PyTierra.git
cd PyTierra
uv sync --extra gui      # includes PySide6 + pyqtgraph
```

### Install with pip

```bash
pip install -e ".[gui]"
```

For headless/CLI-only usage, omit `[gui]`:

```bash
pip install -e .
```

## Your First Simulation

### GUI

1. Launch: `pytierra-gui`
2. The **New Soup** dialog appears. Defaults are good for a first run:
   - Soup size: 60,000 (Small)
   - Ancestor: Built-in 0080aaa
3. Click **OK**
4. Press **Space** to start evolution
5. Watch the soup fill with colored pixels — each color represents an instruction type

### CLI

```bash
pytierra run --ancestor Tierra6_02/tierra/gb0/0080aaa.tie -n 10M
```

This runs 10 million instructions and prints periodic status reports.

## Understanding the Output

### Status Bar

The GUI status bar shows:
- **Inst:** Total instructions executed
- **Cells:** Number of living creatures
- **Fullness:** Percentage of soup occupied
- **IPS:** Instructions per second (performance)

### CLI Reports

```
InstExe: 1,000,000  Cells: 42  Genotypes: 3  AvgSize: 78  Free: 45.2%  Speed: 523,000 inst/s
```

### Genotype Names

Genotype names follow the Tierra convention: `NNNNxxx` where:
- `NNNN` = genome size in decimal (e.g., `0080`)
- `xxx` = three-letter label within that size class (`aaa`, `aab`, `aac`, ...)

Example: `0080aaa` is the original 80-instruction ancestor. `0045aaa` would be the first 45-instruction genotype discovered.

## Save and Load

### Save a Session

- **GUI:** File > Save (Cmd+S) or File > Save As (Cmd+Shift+S)
- Sessions are saved as `.pytierra` files containing complete simulation state

### Open a Session

- **GUI:** File > Open (Cmd+O) or File > Recent Files
- The simulation resumes exactly where it left off, including RNG state

## Export Data

### Soup Image

File > Export > Soup Image as PNG saves the current soup visualization.

### Graph Data

File > Export > Graph Data as CSV exports all time-series data (population, mean size, fitness, genotype count, fullness, IPS) aligned by instruction count.

## Profiling

```bash
pytierra profile -n 1M --output profile.prof
```

This runs 1M instructions under cProfile and prints the top functions by cumulative time, plus the achieved IPS. The `.prof` file can be opened with `snakeviz` or `pstats` for deeper analysis.

## Next Steps

- [Instruction Set](instruction-set.md) — learn what each instruction does
- [Parameters](parameters.md) — tune mutation rates and selection pressure
- [GUI Reference](gui-reference.md) — explore all tabs and features
- [Ancestor Organism](ancestor.md) — understand how the first creature replicates
