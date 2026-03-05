#!/usr/bin/env python
"""Plot subcommand — visualise monitor TSV log files."""

import csv
import sys
from pathlib import Path

from . import __version__


# ---------------------------------------------------------------------------
# Unit parsing
# ---------------------------------------------------------------------------

# Multipliers for inode counts (K, M, G, T)
_INODE_MULT = {'SU': 1, 'K': 1e3, 'M': 1e6, 'G': 1e9, 'T': 1e12}

# Multipliers for byte sizes — always stored as XiB in quota output
_BYTE_MULT = {
    'B':   1,
    'KiB': 2**10, 'MiB': 2**20, 'GiB': 2**30,
    'TiB': 2**40, 'PiB': 2**50,
    # also accept non-binary suffixes if they appear
    'KB':  1e3,   'MB':  1e6,   'GB':  1e9,   'TB':  1e12,
}

# Display labels and divisors for auto-scaling inode counts
_INODE_SCALE = [
    (1e12, 'T'),
    (1e9,  'G'),
    (1e6,  'M'),
    (1e3,  'K'),
    (1,    ''),
]

# Display labels and divisors for auto-scaling byte sizes
_BYTE_SCALE = [
    (2**50, 'PiB'),
    (2**40, 'TiB'),
    (2**30, 'GiB'),
    (2**20, 'MiB'),
    (2**10, 'KiB'),
    (1,     'B'),
]


def _parse_value(token):
    """Parse a value+unit token like '32.86 M*', '574.89 TiB', '622.37 K'.

    Returns (float_in_base_units, over_quota: bool).
    Base unit is 1 (count) for inode metrics and bytes for storage metrics.
    Returns (None, False) if unparseable.
    """
    if not token or token.strip() in ('', '-'):
        return None, False

    token = token.strip()
    over_quota = token.endswith('*')
    token = token.rstrip('*').strip()

    parts = token.split()
    if len(parts) != 2:
        return None, False

    try:
        num = float(parts[0].replace(',', ''))
    except ValueError:
        return None, False

    unit = parts[1].rstrip('*')

    mult = _INODE_MULT.get(unit) or _BYTE_MULT.get(unit)
    if mult is None:
        return None, False

    return num * mult, over_quota


def _best_scale(values, scale_table):
    """Choose display divisor and label from scale_table for a list of base values."""
    max_val = max((v for v in values if v is not None), default=0)
    for threshold, label in scale_table:
        if max_val >= threshold:
            return threshold, label
    return 1, ''


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

def print_help():
    print("NCI Parser v{}  —  plot subcommand".format(__version__))
    print()
    print("Usage: nci-parser plot storage-global <file.tsv> [OPTIONS]")
    print()
    print("Plot time-series data from a monitor log TSV file.")
    print("Each filesystem is drawn as a separate line.")
    print()
    print("Supported table types:")
    print("  storage-global   Plot iused or used over time per filesystem")
    print()
    print("Arguments:")
    print("  storage-global   Table type (required positional)")
    print("  <file.tsv>       Path to the TSV log file produced by 'nci-parser monitor'")
    print()
    print("Options:")
    print("  -h, --help              Show this help message and exit")
    print("  -v, --version           Show version and exit")
    print("  --metric METRIC         Column to plot: 'iused' or 'used' (default: iused)")
    print("  --filesystem FS[,FS]    Plot only these filesystems (comma-separated).")
    print("                          Default: all filesystems in the file.")
    print("  --output FILE           Save plot to FILE (png/pdf/svg) instead of")
    print("                          opening an interactive window.")
    print("  --title TEXT            Override the default plot title.")
    print("  --no-allocation         Do not draw the allocation reference line.")
    print()
    print("Examples:")
    print("  nci-parser plot storage-global fy54.storage-global.tsv")
    print("  nci-parser plot storage-global fy54.storage-global.tsv --metric used")
    print("  nci-parser plot storage-global fy54.storage-global.tsv --filesystem gdata6")
    print("  nci-parser plot storage-global fy54.storage-global.tsv --output plot.png")


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def _plot_storage_global(rows, metric, fs_filter, title, output, no_allocation):
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from datetime import datetime
    except ImportError:
        print("Error: matplotlib is required for plotting.", file=sys.stderr)
        print("Install it with:  pip install matplotlib", file=sys.stderr)
        sys.exit(1)

    # Map metric → corresponding allocation column
    alloc_col = 'iallocation' if metric == 'iused' else 'allocation'

    # Collect data per filesystem:
    # series:  {fs: [(datetime, base_value, over_quota), ...]}
    # allocs:  {fs: float}  — latest non-empty allocation value in base units
    series = {}
    allocs = {}

    for row in rows:
        fs = row.get('filesystem', '').strip()
        if not fs:
            continue
        if fs_filter and fs not in fs_filter:
            continue

        ts_str = row.get('polled_at', '').strip()
        try:
            ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue

        raw = row.get(metric, '').strip()
        base_val, over_quota = _parse_value(raw)
        if base_val is None:
            continue

        series.setdefault(fs, []).append((ts, base_val, over_quota))

        alloc_raw = row.get(alloc_col, '').strip()
        alloc_val, _ = _parse_value(alloc_raw)
        if alloc_val is not None:
            allocs[fs] = alloc_val

    if not series:
        print("Error: No plottable data found. Check --metric and --filesystem options.",
              file=sys.stderr)
        sys.exit(1)

    # Sort each series by time
    for fs in series:
        series[fs].sort(key=lambda x: x[0])

    # Choose display scale — include allocation values so the reference lines fit
    all_vals = [v for pts in series.values() for _, v, _ in pts]
    all_vals += [v for v in allocs.values()]
    scale_table = _BYTE_SCALE if metric == 'used' else _INODE_SCALE
    divisor, unit_label = _best_scale(all_vals, scale_table)

    fig, ax = plt.subplots(figsize=(12, 5))

    prop_cycle = plt.rcParams['axes.prop_cycle']
    colors = [c['color'] for c in prop_cycle]

    for idx, (fs, pts) in enumerate(sorted(series.items())):
        color = colors[idx % len(colors)]
        times   = [p[0] for p in pts]
        vals    = [p[1] / divisor for p in pts]
        oq_mask = [p[2] for p in pts]

        # --- draw the base line (normal colour, thin) ---
        ax.plot(times, vals, color=color, linewidth=1.5, label=fs, zorder=2)

        # --- normal points (not over quota) ---
        norm_t = [t for t, oq in zip(times, oq_mask) if not oq]
        norm_v = [v for v, oq in zip(vals,  oq_mask) if not oq]
        if norm_t:
            ax.scatter(norm_t, norm_v, color=color, s=18, zorder=3)

        # --- over-quota points: red fill, star marker ---
        oq_t = [t for t, oq in zip(times, oq_mask) if oq]
        oq_v = [v for v, oq in zip(vals,  oq_mask) if oq]
        if oq_t:
            ax.scatter(oq_t, oq_v,
                       color='red', edgecolors=color, linewidths=0.8,
                       marker='*', s=120, zorder=4,
                       label=f'{fs} — over quota')

        # --- allocation reference line ---
        if not no_allocation and fs in allocs:
            alloc_disp = allocs[fs] / divisor
            ax.axhline(alloc_disp, color=color, linewidth=1,
                       linestyle='--', alpha=0.6,
                       label=f'{fs} allocation ({alloc_disp:.2f} {unit_label})')

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate()

    metric_label = f'iUsed ({unit_label})' if metric == 'iused' else f'Used ({unit_label})'
    ax.set_ylabel(metric_label)
    ax.set_xlabel('Time')

    default_title = f'Storage {metric} over time'
    ax.set_title(title or default_title)
    ax.legend(loc='best', fontsize='small')
    ax.grid(True, linestyle='--', alpha=0.4)

    fig.tight_layout()

    if output:
        fig.savefig(output, dpi=150)
        print(f"Plot saved to {output}", file=sys.stderr)
    else:
        plt.show()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def plot_main(argv=None):
    """Entry point for the 'plot' subcommand."""
    if argv is None:
        argv = sys.argv[2:]

    if not argv or argv[0] in ['-h', '--help', 'help']:
        print_help()
        sys.exit(0)
    if argv[0] in ['-v', '--version', 'version']:
        print("NCI Parser v{}".format(__version__))
        sys.exit(0)

    args = list(argv)

    # First positional: table type
    table_type = args.pop(0)
    if table_type != 'storage-global':
        print(f"Error: Unknown table type '{table_type}'. Only 'storage-global' is supported.",
              file=sys.stderr)
        sys.exit(1)

    # Defaults
    input_path = None
    metric = 'iused'
    fs_filter = None
    output = None
    title = None
    no_allocation = False

    while args:
        opt = args[0]
        if opt in ['-h', '--help']:
            print_help()
            sys.exit(0)
        elif opt in ['-v', '--version']:
            print("NCI Parser v{}".format(__version__))
            sys.exit(0)
        elif opt == '--metric':
            if len(args) < 2:
                print("Error: --metric requires a value", file=sys.stderr)
                sys.exit(1)
            metric = args[1].lower()
            if metric not in ('iused', 'used'):
                print("Error: --metric must be 'iused' or 'used'", file=sys.stderr)
                sys.exit(1)
            args = args[2:]
        elif opt == '--filesystem':
            if len(args) < 2:
                print("Error: --filesystem requires a value", file=sys.stderr)
                sys.exit(1)
            fs_filter = {f.strip() for f in args[1].split(',')}
            args = args[2:]
        elif opt == '--output':
            if len(args) < 2:
                print("Error: --output requires a value", file=sys.stderr)
                sys.exit(1)
            output = args[1]
            args = args[2:]
        elif opt == '--title':
            if len(args) < 2:
                print("Error: --title requires a value", file=sys.stderr)
                sys.exit(1)
            title = args[1]
            args = args[2:]
        elif opt == '--no-allocation':
            no_allocation = True
            args = args[1:]
        elif opt.startswith('-'):
            print(f"Error: Unknown option '{opt}'", file=sys.stderr)
            sys.exit(1)
        else:
            if input_path is not None:
                print("Error: Only one input file expected", file=sys.stderr)
                sys.exit(1)
            input_path = Path(opt)
            args = args[1:]

    if input_path is None:
        print("Error: Input file is required", file=sys.stderr)
        print("Run 'nci-parser plot --help' for usage.", file=sys.stderr)
        sys.exit(1)

    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(input_path, newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            rows = list(reader)
    except Exception as e:
        print(f"Error: Failed to read {input_path}: {e}", file=sys.stderr)
        sys.exit(1)

    if not rows:
        print(f"Error: No data in {input_path}", file=sys.stderr)
        sys.exit(1)

    # Validate metric column exists
    if metric not in rows[0]:
        available = ', '.join(rows[0].keys())
        print(f"Error: Column '{metric}' not found. Available columns: {available}",
              file=sys.stderr)
        sys.exit(1)

    _plot_storage_global(rows, metric, fs_filter, title, output, no_allocation)


if __name__ == "__main__":
    plot_main()
