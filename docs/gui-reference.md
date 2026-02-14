# GUI Reference

## Main Window Layout

The main window is divided into three areas:

```
┌─────────────────────────────────────────┐
│  Menu Bar                               │
├───────────────┬─────────────────────────┤
│               │                         │
│   Soup View   │      Tab Panel          │
│   (scrollable │   ┌───┬───┬───┬───┐    │
│    with zoom) │   │Dbg│Ins│Inv│Grp│... │
│               │   └───┴───┴───┴───┘    │
│               │                         │
├───────────────┴─────────────────────────┤
│  Toolbar: [Play] [Step] ──Speed──       │
├─────────────────────────────────────────┤
│  Status Bar: Inst | Cells | Full | IPS  │
└─────────────────────────────────────────┘
```

## Soup View

Each pixel represents one memory address, colored by instruction type:

| Color | Instructions |
|-------|-------------|
| Blue | `nop0`, `nop1` (templates) |
| Green | Arithmetic (`not0`, `shl`, `zero`, `ifz`, `sub*`, `inc*`, `dec*`) |
| Yellow/Amber | Stack (`push*`, `pop*`) |
| Red/Orange | Control flow (`jmpo`, `jmpb`, `call`, `ret`) |
| Purple | Data movement (`movDC`, `movBA`, `movii`) |
| Cyan | Addressing (`adro`, `adrb`, `adrf`) |
| White/Pink | Memory & division (`mal`, `divide`) |

### Interaction

- **Mouse hover** — shows address and cell info in status bar
- **Click** — selects a cell, switches to Debug tab
- **Mouse wheel** — zoom in/out
- **Drag** — scroll (via parent scroll area)

## View Overlays

Toggle via the View menu:

- **Show Cells** — colors each creature's memory block by genotype (unique hash-based color)
- **Show IPs** — bright green dots at each creature's instruction pointer position
- **Show Fecundity** — yellow-orange heat overlay on occupied memory regions

## Tabs

### Debug Tab

Displays the selected creature's CPU state:

- **Header** — genotype name, parent, position, fecundity, instruction count, mutations
- **Registers** — AX, BX, CX, DX (decimal and hex)
- **Flags** — E (Error), S (Sign), Z (Zero) as colored indicators
- **Stack** — 10-deep stack with highlighted stack pointer
- **Disassembly** — 21 rows centered on the instruction pointer (highlighted row)
- **Genome bar** — color visualization of the creature's genome

### Inspect Tab

Shows genotype-level information:

- **Header** — name, parent, origin time, population, max population
- **Genome bar** — color visualization
- **Full disassembly** — scrollable text listing every instruction
- **Copy button** — copies disassembly to clipboard

### Inventory Tab

Sortable table of all living genotypes:

| Column | Description |
|--------|-------------|
| Name | Genotype name (e.g., `0080aaa`) |
| Size | Genome length in instructions |
| Population | Current number of living cells |
| Max Pop | Highest population ever reached |
| Parent | Parent genotype name |

- Click column headers to sort
- Type in the filter box to search by name
- Click a row to view that genotype in the Inspect tab

### Graphs Tab

Dropdown selector with 8 views:

**Time Series** (line plots over instruction count):
1. Population Size
2. Mean Creature Size
3. Max Fitness (Fecundity)
4. Genotype Count
5. Soup Fullness (%)
6. Instructions Per Second

**Histograms** (bar charts):
7. Size Histogram — distribution of genome sizes
8. Genotype Frequency — top 20 genotypes by population

### Mutations Tab

Controls for all mutation parameters:

- **Cosmic Ray** (background mutation) rate
- **Copy Error** (movii mutation) rate
- **Execution Flaw** rate
- **Bit-flip probability**
- **Genetic operators** (7 types): crossover, insertion, deletion at instruction and segment level

**Presets:** None, Low, Med, High, Very High — for quick adjustment.

Live rate display shows actual per-instruction probabilities.

### Selection Tab

- **Base slice size** — instructions per time slice
- **Size-dependent slicing** — larger creatures get proportionally more time
- **Slice power** — exponent for size scaling
- **Slice variation** — fixed and random fractions
- **Lazy tolerance** — how long a non-reproducing creature survives

### Settings Tab

- **Memory allocation mode** — first-fit, better-fit, random, near-parent, near-address
- **Reaper settings** — random proportion, near-address reaping, tolerance
- **Division constraints** — require same size, require same genotype, copy threshold
- **Cell constraints** — minimum cell size, search limit
- **Disturbance** — kill proportion for mass extinction events

## Menus

### File Menu

| Item | Shortcut | Description |
|------|----------|-------------|
| New Soup... | Cmd+N | Create a new simulation |
| Open... | Cmd+O | Open a saved `.pytierra` session |
| Save | Cmd+S | Save current session |
| Save As... | Cmd+Shift+S | Save to a new file |
| Recent Files | — | Submenu of up to 10 recent files |
| Export > Soup Image as PNG... | — | Export soup visualization |
| Export > Graph Data as CSV... | — | Export time-series data |
| Quit | Cmd+Q | Exit application |

### Simulation Menu

| Item | Shortcut | Description |
|------|----------|-------------|
| Play/Pause | Space | Toggle simulation |
| Step | Right arrow | Execute one time slice |
| Speed Up | `]` | Increase speed |
| Speed Down | `[` | Decrease speed |

### View Menu

| Item | Shortcut | Description |
|------|----------|-------------|
| Show Cells | — | Toggle cell overlay |
| Show IPs | — | Toggle instruction pointer overlay |
| Show Fecundity | — | Toggle fecundity heat overlay |
| Zoom In | Cmd++ | Zoom soup view in |
| Zoom Out | Cmd+- | Zoom soup view out |
| Zoom to Fit | Cmd+0 | Fit entire soup in view |

### Window Menu

| Item | Shortcut | Description |
|------|----------|-------------|
| Genebank | Cmd+G | Open genebank window |

### Help Menu

| Item | Shortcut | Description |
|------|----------|-------------|
| PyTierra Help | F1 | Open help window |
| About PyTierra | — | Version and credits |

## Keyboard Shortcuts Summary

| Key | Action |
|-----|--------|
| Space | Play / Pause |
| Right | Step one slice |
| `]` | Speed up |
| `[` | Speed down |
| Cmd+N | New Soup |
| Cmd+O | Open Session |
| Cmd+S | Save Session |
| Cmd+Shift+S | Save As |
| Cmd+G | Genebank |
| Cmd++ | Zoom In |
| Cmd+- | Zoom Out |
| Cmd+0 | Zoom to Fit |
| F1 | Help |

## Genebank Window

Separate window for browsing the persistent genotype database:

- **Table** — all collected genotypes with name, size, max pop, origin, parent, last seen
- **Filter** — search by name
- **Inject** — add a stored genotype back into the running soup
- **Export** — save as `.tie` file
- **Delete** — remove from database
- **Refresh** — manually collect from current simulation

The genebank auto-collects qualifying genotypes approximately every 2 seconds.

## Dark Mode

PyTierra automatically detects the system color scheme on startup. On macOS with dark mode enabled, the application uses a dark palette. The pyqtgraph plots always use a dark background regardless of mode.
