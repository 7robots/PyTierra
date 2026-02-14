"""Shared path resolution for bundled data files."""

from pathlib import Path


def default_ancestor_path() -> Path | None:
    """Resolve path to the built-in 0080aaa ancestor genome.

    Tries in order:
    1. importlib.resources (installed package)
    2. data/genomes/ relative to project root (development checkout)

    Returns None if the file cannot be found.
    """
    # 1. Installed package data
    try:
        from importlib.resources import files
        pkg_path = files("pytierra").joinpath("data", "0080aaa.tie")
        resolved = Path(str(pkg_path))
        if resolved.exists():
            return resolved
    except Exception:
        pass

    # 2. Development checkout: <project-root>/data/genomes/
    project_root = Path(__file__).parent.parent
    dev_path = project_root / "data" / "genomes" / "0080aaa.tie"
    if dev_path.exists():
        return dev_path

    return None
