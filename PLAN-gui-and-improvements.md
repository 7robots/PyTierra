# PyTierra: GUI & Future Development Plan

## Overview

This plan covers two tracks of work: (A) closing fidelity gaps between PyTierra and the original Tierra 6.02, and (B) building a cross-platform GUI modeled after MacTierra. The GUI will use PySide6 (Qt for Python) for native look and feel on macOS, Linux, and Windows, with NumPy-backed rendering for the soup visualization.

The plan is organized into 7 phases, designed so each phase produces a usable increment.

---

## Phase 1: Engine Hardening & Fidelity Gaps

**Goal:** Bring the simulation engine to full Tierra 6.02 parity before building UI on top of it.

### 1.1 Full Genetic Operators (`mutations.py`)
- **Crossover (same-size):** Exchange instruction segments between mother genome and a random same-size genome in the soup (`GenPerCroInsSamSiz`)
- **Crossover (size-changing):** Exchange segments allowing daughter size to change (`GenPerCroIns`)
- **Segment-level insertion/deletion/crossover:** Operate on NOP-bounded segments rather than individual instructions (`GenPerDelSeg`, `GenPerInsSeg`, `GenPerCroSeg`)
- Port the C helper functions: `CountSegments()`, `FindStartSegN()`, `FindEndSegN()`, `SharedGenOps()` (temporary buffer assembly with reallocation)

### 1.2 Size-Dependent Slicing (`scheduler.py`)
- Implement `SizDepSlice` mode: `slice = cell.mm.size ^ SlicePow`
- Implement `SliceStyle=2`: `slice = (SlicFixFrac * base) + random(SlicRanFrac * base)`
- Wire `slice_pow`, `slic_fix_frac`, `slic_ran_frac` config params into the scheduler

### 1.3 Memory Protection (`soup.py`, `instructions.py`)
- Implement `MemModeFree` (rwx for free memory), `MemModeMine` (rwx for own memory), `MemModeProt` (rwx for others' memory)
- Bit flags: 1=execute, 2=write, 4=read
- Check protection in `movii`, `movid`, soup reads, and instruction fetch
- Error flag set on protection violation

### 1.4 Reaper Near-Address Mode (`reaper.py`)
- When `MalReapTol=1` and allocation fails: search the reaper queue for the oldest cell within `MalTol * avg_size` of the requested address
- Fall back to global reaper if no nearby candidate found

### 1.5 Disturbance System (`simulation.py`)
- Implement `DistFreq` / `DistProp`: periodically kill a random fraction of the population
- Frequency calculated relative to recovery time (negative `DistFreq` = factor of recovery time)

### 1.6 Save/Restore Simulation State
- **Module:** `persistence.py`
- Serialize complete simulation state: soup data, all cells (CPU state, demographics), scheduler queue order, reaper queue order, genebank, instruction counter, RNG state
- Format: compressed binary (pickle with protocol 5 for numpy arrays, or msgpack)
- CLI: `pytierra save --output state.pyt` / `pytierra load --input state.pyt`

### 1.7 Genome Disk Bank (`genome_io.py`, `genebank.py`)
- Auto-save genotypes meeting thresholds (`SavMinNum`, `SavThrMem`, `SavThrPop`) to disk in `.tie` format
- Configurable save path (`GenebankPath`)
- Periodic save at `SaveFreq` million instructions

### Tests
- Unit tests for each genetic operator (verify segment counting, crossover produces valid genomes)
- Test size-dependent slicing gives larger cells more cycles
- Test memory protection blocks unauthorized writes
- Test save/restore round-trip produces identical simulation state
- Test disturbance reduces population by expected proportion

---

## Phase 2: Simulation Data Collection & Event System

**Goal:** Build the data infrastructure the GUI will consume — time-series logging, event notifications, and a clean API boundary between engine and UI.

### 2.1 Data Loggers (`datalog.py`)
- `TimeSeriesLog`: ring buffer of `(instruction_count, value)` tuples, configurable capacity (default 10K points)
- Built-in series:
  - `population_size` — number of living cells
  - `mean_creature_size` — average genome length
  - `max_fitness` — highest fecundity in population
  - `num_genotypes` — count of distinct living genotypes
  - `soup_fullness` — percentage of soup occupied
  - `instructions_per_second` — throughput
- `SizeHistogram`: snapshot of creature size distribution
- `GenotypeFrequency`: snapshot of top-N genotype populations
- Configurable sample interval (default: every 1000 slicer cycles)

### 2.2 Event System (`events.py`)
- Simple observer pattern: `sim.events.subscribe(event_type, callback)`
- Event types:
  - `CELL_BORN` — new cell created (divide), payload: cell, parent
  - `CELL_DIED` — cell reaped, payload: cell, cause (lazy/reaper/disturbance)
  - `NEW_GENOTYPE` — first occurrence of a genotype, payload: genotype
  - `GENOTYPE_EXTINCT` — last cell of genotype died, payload: genotype
  - `MILESTONE` — configurable instruction count milestones
  - `MUTATION` — background or copy mutation occurred
- Callbacks run synchronously within the engine loop; GUI will bridge these to Qt signals on the main thread

### 2.3 Simulation Controller API (`controller.py`)
- Thread-safe wrapper around `Simulation`:
  - `start()` / `pause()` / `step(n=1)` / `stop()`
  - `set_speed(instructions_per_step)` — controls how many instructions run per tick
  - `get_cell(cell_id) -> CellSnapshot` — immutable snapshot of cell state
  - `get_genotype(name) -> GenotypeSnapshot`
  - `get_soup_image(width, height) -> numpy.ndarray` — rendered RGBA image of soup
  - `inject_genome(genome_bytes, position)` — add a creature at runtime
  - `update_config(**kwargs)` — modify settings live
- Runs simulation on a background `threading.Thread`, emits Qt-compatible signals via `QObject` bridge

### Tests
- Test data loggers accumulate correct values over a short run
- Test event system fires correct events for birth/death/mutation
- Test controller pause/resume maintains consistent state
- Test soup image generation produces expected dimensions

---

## Phase 3: Main Window & Soup Visualization

**Goal:** A functional application window with the soup view and basic playback controls. This is the first visible GUI milestone.

### 3.1 Application Skeleton (`gui/app.py`)
- **Framework:** PySide6
- `QApplication` subclass with dark/light theme support
- Application icon, menu bar (File, Edit, View, Soup, Window, Help)
- `QMainWindow` with central split layout matching MacTierra:
  - Left: Soup view (resizable)
  - Right: Tabbed panel
  - Bottom: Status bar

### 3.2 Soup Visualization (`gui/soup_view.py`)
- **Widget:** Custom `QWidget` subclass with `paintEvent` override
- Renders soup as a 2D grid of colored pixels (one pixel per instruction)
- Grid width fixed at 512 (or configurable); height = ceil(soup_size / width)
- **Color scheme:** 32 distinct colors for each opcode (matching Tierra conventions — NOPs blue, arithmetic green, stack yellow, jumps red, etc.)
- **Overlay modes** (toggleable from View menu):
  - **Show Cells:** Draw colored rectangles around each cell's memory region, color by genotype hash
  - **Show Instruction Pointers:** Green dot/rectangle at each cell's IP position
  - **Show Fecundity:** Yellow-orange heat map overlay based on cell fecundity
- **Interaction:**
  - Click on soup to select the creature at that address
  - Mouse hover shows address and creature name in status bar
  - Scroll wheel zooms in/out
  - Drag-and-drop genotypes from genebank onto soup to inject
- **Performance:** Render to a `QImage` backed by numpy RGBA array; only re-render on simulation tick (not every paint), cache between frames
- Zoom-to-fit button in toolbar

### 3.3 Playback Controls
- **Toolbar:** Play/Pause button, Step button, Speed slider (logarithmic: 1 slice/tick to 10K slices/tick)
- **Keyboard shortcuts:** Space = play/pause, Right arrow = step, +/- = speed
- **Status bar:** Instructions executed, slicer cycles, cells alive, soup fullness %, IPS (instructions per second)
- Timer-driven: `QTimer` fires at 30-60 fps, each tick runs N slices then updates display

### 3.4 New Soup Dialog (`gui/new_soup_dialog.py`)
- Modal dialog for creating a new simulation
- Fields: soup size (presets + custom), random seed, ancestor selection (file picker or built-in 0080aaa)
- "Create" opens a new document window with the configured simulation

### Dependencies
- `PySide6` (add to `pyproject.toml` optional-dependencies `[gui]`)
- Entry point: `pytierra-gui` or `python -m pytierra.gui`

---

## Phase 4: Tabbed Panels — Debug, Inspect, Inventory

**Goal:** The three information-display tabs that let users examine individual creatures and the population.

### 4.1 Debug Tab (`gui/tabs/debug_tab.py`)
- **Selected creature info:** Name, parent genotype, memory location, size, IP
- **Statistics:** Offspring count, instructions executed, mutations
- **CPU state panel:**
  - Registers: ax, bx, cx, dx (displayed as decimal and hex)
  - Flags: E, S, Z (colored indicators)
  - Stack: 10-entry table showing values and stack pointer position
- **Soup around IP:** Disassembly view showing ~20 instructions around the current IP
  - Current instruction highlighted
  - Address, opcode hex, mnemonic, comment (nop template annotations)
  - Updates each simulation step
- **Genotype image:** Horizontal color bar rendering the creature's genome (each instruction = colored stripe)

### 4.2 Inspect Tab (`gui/tabs/inspect_tab.py`)
- **Genotype info:** Name, parent, origin generation, origin instruction count, max population
- **Full genome disassembly:** Scrollable text view with line numbers, mnemonics, and hex opcodes
- **Genotype image:** Larger version of the colored genome bar
- **Copy genome** button (copies disassembly to clipboard)

### 4.3 Inventory Tab (`gui/tabs/inventory_tab.py`)
- **Table view** (`QTableView` + custom model) showing all living genotypes:
  - Columns: Name, Size, Alive (current pop), Ever (total born), Generation, Genome bar (inline color rendering)
  - Sortable by any column
  - Click to select → updates Inspect tab
- **Filter:** Text field to filter by name/size
- **Drag-and-drop:** Drag genotype row to soup view to inject, or to genebank to save
- Only shows genotypes with population > 0 (refreshes on timer)

---

## Phase 5: Graphs Tab

**Goal:** Real-time time-series graphs and histograms showing evolutionary dynamics.

### 5.1 Graph Framework (`gui/tabs/graph_tab.py`)
- **Library:** `pyqtgraph` (fast, Qt-native plotting — add to `[gui]` dependencies)
- **Dropdown selector** to switch between graph types
- Auto-updating: graph refreshes on each data logger sample

### 5.2 Time-Series Graphs
- **Population Size vs Time** — line plot, X = instructions (or slicer cycles), Y = cell count
- **Mean Creature Size vs Time** — line plot showing average genome length trend
- **Max Fitness vs Time** — line plot showing highest fecundity in population
- **Two Genotypes Frequency** — dual line plot comparing two selected genotypes
  - Auxiliary panel with dropdowns to select two genotypes
  - Side-by-side genotype images below the graph
- All graphs support:
  - X-axis toggle: instructions / slicer cycles
  - Auto-scale Y axis
  - Pan and zoom
  - Export to PNG

### 5.3 Histogram Views
- **Genotype Frequency Histogram** — bar chart of top-N genotypes by population
- **Size Histogram** — bar chart showing distribution of creature sizes
- Both update periodically (every N slicer cycles)

---

## Phase 6: Settings Panels & Genebank Window

**Goal:** Full configuration UI and the persistent genotype database.

### 6.1 Settings Tabs
Each settings tab binds bidirectionally to the `Config` object; changes take effect immediately on the running simulation.

**Mutation Tab (`gui/tabs/mutation_tab.py`):**
- Three sections: Cosmic Ray, Copy Error, Execution Flaw
- Each with: slider (generations per mutation), computed rate display, preset buttons (None/Low/Med/High/Very High)
- Mutation type toggle: random instruction vs. bit flip (controlled by `mut_bit_prop`)
- "Zero All Rates" button

**Selection Tab (`gui/tabs/selection_tab.py`):**
- Slice size: constant (slider) or size-dependent (checkbox + power slider)
- Random variation in slice size (percentage slider)
- Lazy tolerance slider

**Other Settings Tab (`gui/tabs/other_settings_tab.py`):**
- Daughter allocation mode (dropdown: first fit, better fit, random, near mother, near bx)
- Reaper settings: reap proportion slider, near-address reaping toggle
- Division constraints: same-size checkbox, same-genotype checkbox
- Min cell size spinner
- MovPropThrDiv slider
- Search limit multiplier

### 6.2 Genebank Window (`gui/genebank_window.py`)
- **Separate `QMainWindow`** accessible from Window menu
- **Persistent SQLite database** using Python `sqlite3` module
  - Location: `~/.pytierra/genebank.db`
  - Schema: genotypes table (name, size, genome blob, origin_time, parent, max_pop, first_seen, last_seen)
- **Table view** with columns: Name, Size, Max Population, Origin, Parent
- **Actions:**
  - Drag genotype from genebank into soup view → injects creature
  - Right-click → Export to .tie file
  - Right-click → Delete from genebank
  - Search/filter bar
- **Auto-collection:** Genotypes meeting population threshold automatically saved to genebank
- **Import:** Drag .tie files onto genebank window to add

---

## Phase 7: Polish, Performance & Distribution

**Goal:** Production-quality application ready for distribution.

### 7.1 Performance Optimization
- **Profile** the inner loop (`run_slice`) with cProfile
- **Cython acceleration** for the hot path: compile `run_slice`, instruction dispatch, soup read/write, and template matching to C extensions
  - Target: 10-50x speedup (from ~400K to 5-20M inst/s)
  - Fallback: pure Python for PyPy compatibility
- **Soup rendering:** Use `QOpenGLWidget` if `QImage` approach can't maintain 30fps at large soup sizes
- **Batch UI updates:** Accumulate N simulation ticks before updating all widgets (configurable via speed slider)

### 7.2 File Format & Session Management
- **Document model:** Each simulation is a "document" that can be saved/opened
  - File extension: `.pytierra`
  - Contains: serialized simulation state + config + RNG state
- **Auto-save** at configurable intervals
- **Recent files** in File menu
- **Export options:**
  - Export configuration as `.ini` (Tierra si0 format, for compatibility)
  - Export genotype as `.tie`
  - Export graph data as CSV
  - Export soup image as PNG

### 7.3 Application Packaging
- **macOS:** Bundle as `.app` using `py2app` or `briefcase`
  - Application icon, Info.plist, code signing
  - Universal binary (arm64 + x86_64) via fat numpy wheels
- **Linux:** AppImage or Flatpak
- **Windows:** NSIS installer or MSIX via `briefcase`
- **PyPI:** `pip install pytierra[gui]` for users who want to install from source

### 7.4 UI Polish
- **Dark mode** support (follow system theme)
- **Retina/HiDPI** rendering for soup view
- **Keyboard shortcuts** for all major actions (matching MacTierra where sensible)
- **Tooltips** on all controls
- **Help window** with brief Tierra primer and control reference
- **About dialog** with version, credits, link to Tom Ray's original work

---

## Module Structure (Final)

```
pytierra/
├── __init__.py
├── config.py
├── soup.py
├── cpu.py
├── cell.py
├── instructions.py
├── scheduler.py
├── reaper.py
├── genebank.py
├── mutations.py
├── simulation.py
├── genome_io.py
├── cli.py
├── __main__.py
├── persistence.py        # Phase 1.6
├── datalog.py            # Phase 2.1
├── events.py             # Phase 2.2
├── controller.py         # Phase 2.3
└── gui/
    ├── __init__.py
    ├── app.py             # Phase 3.1 — QApplication, main window
    ├── soup_view.py       # Phase 3.2 — Soup visualization widget
    ├── new_soup_dialog.py # Phase 3.4 — New simulation dialog
    ├── genebank_window.py # Phase 6.2 — Persistent genebank
    ├── status_bar.py      # Phase 3.3 — Status bar widget
    ├── resources/         # Icons, color maps
    │   ├── colors.py      # Opcode color definitions
    │   └── icons/
    └── tabs/
        ├── __init__.py
        ├── debug_tab.py     # Phase 4.1
        ├── inspect_tab.py   # Phase 4.2
        ├── inventory_tab.py # Phase 4.3
        ├── graph_tab.py     # Phase 5.1
        ├── mutation_tab.py  # Phase 6.1
        ├── selection_tab.py # Phase 6.1
        └── settings_tab.py  # Phase 6.1
```

## Dependency Summary

| Package | Purpose | Phase |
|---|---|---|
| `numpy` | Soup array, rendering buffers | Already present |
| `PySide6` | Qt GUI framework | Phase 3 |
| `pyqtgraph` | Fast plotting | Phase 5 |
| `Cython` (optional) | Performance acceleration | Phase 7 |

## Key Design Decisions

1. **PySide6 over Tkinter/wxPython:** Native look on all platforms, excellent widget library, good Python bindings, active maintenance by Qt Company.
2. **pyqtgraph over matplotlib:** Designed for real-time data, GPU-accelerated, integrates natively with Qt (no embedding hacks).
3. **Background thread for simulation:** GUI stays responsive. Controller bridges engine events to Qt signals via `QMetaObject.invokeMethod` for thread safety.
4. **Numpy-backed rendering:** The soup image is a numpy RGBA array that gets blitted to a `QImage`; overlays (cells, IPs, fecundity) are composited in numpy before painting. This avoids per-pixel Qt draw calls.
5. **Observer pattern for events:** Decouples engine from GUI. The CLI can subscribe to the same events for text output. Makes testing easy.
