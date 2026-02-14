# Architecture

## Module Diagram

```
pytierra/
├── simulation.py      Main loop orchestration
├── soup.py            Memory array + free block allocator
├── cell.py            Cell, MemRegion, Demographics
├── cpu.py             CPU state (registers, flags, stack)
├── instructions.py    32 instruction implementations + dispatch table
├── scheduler.py       Round-robin scheduler with time slicing
├── reaper.py          Fitness-based memory reaper
├── genebank.py        Genotype tracking and naming
├── mutations.py       Mutation operators (cosmic ray, copy, flaw, genetic)
├── events.py          EventBus for decoupled notifications
├── config.py          Configuration dataclass + si0 file loader
├── persistence.py     Save/load full simulation state (pickle)
├── datalog.py         Time-series data collection
├── genome_io.py       .tie file reader/writer
├── controller.py      Thread-safe GUI wrapper
├── cli.py             Command-line interface
│
├── gui/
│   ├── app.py             Main window, menus, toolbar
│   ├── soup_view.py       Soup visualization widget
│   ├── status_bar.py      Metrics display
│   ├── new_soup_dialog.py Config dialog
│   ├── genebank_window.py SQLite genebank browser
│   ├── help_window.py     HTML help viewer
│   └── tabs/
│       ├── debug_tab.py         CPU/disassembly inspector
│       ├── inspect_tab.py       Genotype viewer
│       ├── inventory_tab.py     Population table
│       ├── graph_tab.py         Real-time plots
│       ├── mutation_tab.py      Mutation controls
│       ├── selection_tab.py     Selection controls
│       └── other_settings_tab.py Advanced settings
│
└── tests/             12 test modules, 84+ tests
```

## Component Relationships

```
                    ┌─────────────┐
                    │  CLI / GUI  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Controller │  (thread-safe wrapper)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ Simulation  │  (main loop)
                    └──┬──┬──┬───┘
         ┌─────────────┤  │  ├─────────────┐
         ▼             ▼  ▼  ▼             ▼
    ┌─────────┐  ┌────┐ ┌────────┐  ┌──────────┐
    │ Scheduler│  │Soup│ │Genebank│  │ Mutations │
    └────┬────┘  └──┬─┘ └────────┘  └──────────┘
         │         │
    ┌────▼────┐    │    ┌────────┐
    │  Cells  ├────┘    │ Reaper │
    └────┬────┘         └────────┘
         │
    ┌────▼────┐
    │   CPU   │
    └─────────┘
```

## Key Design Decisions

### Soup as numpy array

The soup is a flat `numpy.uint8` array. This enables fast bulk reads for visualization (`get_soup_image`) and efficient memory operations. Individual instruction reads/writes use direct indexing with modular arithmetic for address wrapping.

### Thread-safe controller

The `SimulationController` wraps the `Simulation` in a lock-protected interface. The simulation runs on a background thread in a tight loop. The GUI thread reads snapshots (immutable `CellSnapshot` / `GenotypeSnapshot` dataclasses) without blocking the simulation for long.

### Immutable snapshots

All data crossing the thread boundary is copied into frozen dataclasses. This eliminates race conditions between the simulation thread modifying cell state and the GUI thread reading it.

### Event-driven architecture

The `EventBus` emits events like `CELL_BORN` and `NEW_GENOTYPE` for decoupled notification. This allows the genebank, UI, and other systems to react without tight coupling.

### Pickle-based persistence

Full simulation state is serialized with `pickle` protocol 5. This captures everything needed for bit-exact resumption: soup data, all cell states, scheduler/reaper queue order, genebank, RNG state.

### Modular instruction set

Each instruction is a standalone function in `instructions.py` with signature `(sim, cell) -> None`. A dispatch table maps opcodes to functions. This makes the instruction set easy to extend or modify.

## Data Flow

### Simulation tick

1. Scheduler selects current cell
2. `run_slice()` executes N instructions (N = computed slice size)
3. Each instruction: read opcode → dispatch → execute → advance IP
4. Mutations may occur (background, copy, flaw)
5. Reaper checks lazy tolerance at end of slice
6. Scheduler advances to next cell

### GUI refresh cycle

1. Background thread runs batches of slices, calls tick callback
2. QTimer fires at 30fps
3. `_update_ui()` reads controller snapshots under lock
4. Soup image rendered (numpy → QImage)
5. Active tab refreshed (debug/inventory/graphs)
6. Status bar updated with metrics

### Genebank collection

1. During `divide`, new cell's genome is hashed and registered
2. If it's a new genotype, a name is assigned (size + label)
3. GUI auto-collects qualifying genotypes to SQLite every ~2 seconds
4. Disk genebank saves .tie files periodically based on thresholds
