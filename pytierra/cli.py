"""Command-line entry point for PyTierra."""

import argparse
import sys
import time
from pathlib import Path

from .config import Config
from .simulation import Simulation


def parse_instruction_count(s: str) -> int:
    """Parse instruction count with optional K/M/G suffix."""
    s = s.strip().upper()
    multipliers = {"K": 1_000, "M": 1_000_000, "G": 1_000_000_000}
    for suffix, mult in multipliers.items():
        if s.endswith(suffix):
            return int(float(s[:-1]) * mult)
    return int(s)


def main(args=None):
    parser = argparse.ArgumentParser(
        prog="pytierra",
        description="PyTierra: Python Tierra artificial life simulator",
    )
    subparsers = parser.add_subparsers(dest="command")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run a simulation")
    run_parser.add_argument("--config", "-c", type=str, default=None,
                            help="Path to Tierra config file (si0 format)")
    run_parser.add_argument("--ancestor", "-a", type=str, default=None,
                            help="Path to ancestor .tie genome file")
    run_parser.add_argument("--instructions", "-n", type=str, default="0",
                            help="Max instructions to execute (0=infinite, supports K/M/G suffixes)")
    run_parser.add_argument("--report-interval", "-r", type=str, default="1M",
                            help="Instructions between status reports")
    run_parser.add_argument("--soup-size", type=int, default=None,
                            help="Override soup size")
    run_parser.add_argument("--seed", type=int, default=None,
                            help="Random seed (0=use time)")
    run_parser.add_argument("--quiet", "-q", action="store_true",
                            help="Suppress periodic output")

    # GUI command
    subparsers.add_parser("gui", help="Launch the graphical interface")

    # Profile command
    profile_parser = subparsers.add_parser("profile", help="Profile simulation performance")
    profile_parser.add_argument("--instructions", "-n", type=str, default="1M",
                                help="Instructions to execute (supports K/M/G suffixes, default: 1M)")
    profile_parser.add_argument("--ancestor", "-a", type=str, default=None,
                                help="Path to ancestor .tie genome file")
    profile_parser.add_argument("--soup-size", type=int, default=60000,
                                help="Soup size (default: 60000)")
    profile_parser.add_argument("--output", "-o", type=str, default=None,
                                help="Save .prof file for external analysis")

    parsed = parser.parse_args(args)

    if parsed.command is None:
        parser.print_help()
        return 1

    if parsed.command == "run":
        return run_simulation(parsed)

    if parsed.command == "gui":
        from .gui.app import run_gui
        return run_gui()

    if parsed.command == "profile":
        return run_profile(parsed)

    return 0


def run_simulation(args) -> int:
    config = Config()
    if args.config:
        config = Config.load(args.config)
    if args.soup_size is not None:
        config.soup_size = args.soup_size
    if args.seed is not None:
        config.seed = args.seed

    sim = Simulation(config=config)

    max_inst = parse_instruction_count(args.instructions)
    report_interval = parse_instruction_count(args.report_interval)

    # Boot
    if args.ancestor:
        sim.boot(args.ancestor)
    elif args.config:
        # Try to use inoculation list from config
        config_dir = str(Path(args.config).parent)
        genebank_dir = str(Path(config_dir) / config.genebank_path)
        sim.boot_from_config(genebank_dir)

    if sim.scheduler.num_cells == 0:
        print("Error: No cells in simulation. Provide --ancestor or --config with inoculations.", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"PyTierra starting: soup_size={config.soup_size}, cells={sim.scheduler.num_cells}")
        print(f"Running for {'infinite' if max_inst == 0 else f'{max_inst:,}'} instructions...")

    start = time.time()
    sim._start_time = start
    last_report = 0

    try:
        while max_inst == 0 or sim.inst_executed < max_inst:
            cell = sim.scheduler.current()
            if cell is None:
                break
            sim.run_slice(cell)
            sim.scheduler.advance()

            # Periodic bookkeeping & reporting
            if sim.inst_executed - last_report >= report_interval:
                sim._periodic_bookkeeping()
                if not args.quiet:
                    print(sim.report())
                last_report = sim.inst_executed

                # Drop dead check
                if config.drop_dead > 0:
                    dead_threshold = config.drop_dead * 1_000_000
                    if sim.inst_executed - sim.last_repro_inst > dead_threshold:
                        if not args.quiet:
                            print("Drop dead: no reproduction detected. Stopping.")
                        break
    except KeyboardInterrupt:
        if not args.quiet:
            print("\nInterrupted.")

    elapsed = time.time() - start
    if not args.quiet:
        print(f"\nFinal: {sim.report()}")
        print(f"Elapsed: {elapsed:.1f}s")
        if sim.genebank:
            summary = sim.genebank.summary()
            if summary:
                print(f"\nLiving genotypes ({len(summary)}):")
                for name, pop in sorted(summary.items(), key=lambda x: -x[1])[:20]:
                    print(f"  {name}: {pop}")

    return 0


def run_profile(args) -> int:
    """Run simulation under cProfile and print results."""
    import cProfile
    import pstats

    max_inst = parse_instruction_count(args.instructions)

    config = Config()
    config.soup_size = args.soup_size

    sim = Simulation(config=config)

    if args.ancestor:
        sim.boot(args.ancestor)
    else:
        # Use built-in ancestor
        from importlib.resources import files
        ancestor_path = str(files("pytierra").joinpath("data", "0080aaa.tie"))
        if not Path(ancestor_path).exists():
            # Fallback: try Tierra6_02 directory
            fallback = Path(__file__).parent.parent / "Tierra6_02" / "tierra" / "gb0" / "0080aaa.tie"
            if fallback.exists():
                ancestor_path = str(fallback)
            else:
                print("Error: No ancestor genome found. Provide --ancestor.", file=sys.stderr)
                return 1
        sim.boot(ancestor_path)

    if sim.scheduler.num_cells == 0:
        print("Error: No cells booted.", file=sys.stderr)
        return 1

    print(f"Profiling {max_inst:,} instructions (soup_size={config.soup_size})...")

    def _run():
        while sim.inst_executed < max_inst:
            cell = sim.scheduler.current()
            if cell is None:
                break
            sim.run_slice(cell)
            sim.scheduler.advance()

    profiler = cProfile.Profile()
    start = time.time()
    profiler.runcall(_run)
    elapsed = time.time() - start

    ips = sim.inst_executed / elapsed if elapsed > 0 else 0
    print(f"\nCompleted: {sim.inst_executed:,} instructions in {elapsed:.2f}s")
    print(f"Performance: {ips:,.0f} instructions/second")
    print(f"Cells: {sim.scheduler.num_cells}")
    print()

    stats = pstats.Stats(profiler)
    stats.sort_stats("cumulative")
    stats.print_stats(30)

    if args.output:
        profiler.dump_stats(args.output)
        print(f"\nProfile data saved to: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
