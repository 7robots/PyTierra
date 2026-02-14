# Troubleshooting

## Installation Issues

### PySide6 fails to install

PySide6 requires a compatible platform. If installation fails:

```bash
# Try upgrading pip first
pip install --upgrade pip

# On macOS, ensure you have a recent Python
python3 --version  # should be 3.10+
```

If you don't need the GUI, install without it:

```bash
pip install -e .
```

### "No module named 'pytierra'" when running

Make sure you installed in development mode:

```bash
pip install -e .
# or with uv:
uv sync
```

### pyqtgraph import error

Ensure you installed the `gui` extras:

```bash
pip install -e ".[gui]"
```

## Simulation Issues

### "Drop dead: no reproduction detected"

The simulation stops when no creature has reproduced for `drop_dead` million instructions (default: 5M). This usually means:

- **Mutation rate too high** — organisms are corrupted faster than they can replicate. Lower mutation rates in the Mutations tab.
- **Soup too small** — not enough memory for reproduction. Increase soup size.
- **Selection too harsh** — reaper is killing creatures before they can reproduce. Increase `lazy_tol` in the Selection tab.

### Population stays at 1

The ancestor may not be replicating. Check:

1. Is the simulation running? Press Space to start.
2. Is the ancestor genome correct? The built-in 0080aaa should work.
3. Are mutation rates reasonable? Try the "Low" preset.

### Population crashes to 0

Mass extinction. This can happen from:

- **Disturbance events** — if `dist_prop` is too high. Reduce in Settings.
- **Parasites** — parasites may kill all hosts. This is natural in Tierra.
- **Memory fragmentation** — too many free blocks. Check `max_free_blocks`.

### Simulation runs slowly

Performance depends on population size and soup size. Tips:

- Use a smaller soup (60K instead of 6M)
- Reduce the speed slider to lower CPU usage
- Close unnecessary overlay views (Show Cells is expensive)
- Use `pytierra profile` to identify bottlenecks

## GUI Issues

### Window appears blank

The New Soup dialog may be hidden behind the main window. Look for it in your taskbar. If the dialog was cancelled, use File > New Soup.

### Soup view is too small/large

- Cmd++ / Cmd+- to zoom
- Cmd+0 to fit the entire soup in the view
- Mouse wheel also zooms

### Status bar shows 0 IPS

IPS is only calculated while the simulation is running (Play mode). It updates every 0.5 seconds.

### Recent Files menu shows deleted files

Recent files are tracked by path. If you move or delete a `.pytierra` file, the entry remains but will show an error when opened. The list clears naturally as new files are opened.

### Dark mode doesn't apply

Dark mode is detected at startup. If you change your system theme while PyTierra is running, restart the application. On some Linux desktops, dark mode detection may not work — the fallback uses palette brightness analysis.

## File Format Issues

### Can't open .pytierra file

Session files use Python's pickle format. They are not compatible across:
- Different PyTierra versions (if class structure changed)
- Different Python major versions

If you get an unpickling error, the file was likely saved with a different version.

### .tie file won't load

Tierra `.tie` files must contain a `CODE` section. The format is:

```
CODE

track 0:

nop1    ; 0
nop1    ; 1
...
```

Lines before `CODE` are metadata (ignored). Lines starting with `;` are comments. Only recognized mnemonics are loaded.

## Performance Tuning

### Recommended settings for fast evolution

- Soup size: 60,000 (Small)
- Mutation preset: "Med"
- `drop_dead`: 5 (or 0 to disable)
- Close cell overlays for maximum speed

### Recommended settings for observing behavior

- Soup size: 60,000 (Small)
- Speed slider: 20-40 (slow enough to watch)
- Enable "Show Cells" overlay
- Select a creature and watch the Debug tab

## Getting Help

- Press F1 in the GUI for the built-in help window
- See the [docs/](.) directory for detailed documentation
- Report issues at https://github.com/7robots/PyTierra/issues
