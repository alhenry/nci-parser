#!/usr/bin/env python
"""Monitor subcommand — repeatedly poll NCI account data and write parsed TSV output."""

import csv
import datetime
import subprocess
import sys
import time
from pathlib import Path

from .quota_parser import parse_quota_text, VALID_OUTPUTS
from . import __version__


def print_help():
    print("NCI Parser v{}  —  monitor subcommand".format(__version__))
    print()
    print("Usage: nci-parser monitor quota -P <project> [OPTIONS]")
    print()
    print("Repeatedly call 'nci_account -v -P <project>', parse the quota report,")
    print("and write (or overwrite) TSV output files at a fixed interval.")
    print()
    print("Output files are written to --outdir (default: current directory) with")
    print("the stem  '<YYYY-MM-DD>.<project>'  so they match the file naming")
    print("convention used by nci-parser quota:")
    print("  <stem>.usage-global.tsv")
    print("  <stem>.usage-users.tsv")
    print("  <stem>.storage-global.tsv")
    print()
    print("Each poll overwrites the same dated files.  Use --archive to also")
    print("save a timestamped copy alongside them on every successful poll.")
    print()
    print("Required:")
    print("  quota               The type of report to monitor (only 'quota' supported)")
    print("  -P, --project ID    NCI project identifier (e.g. fy54)")
    print()
    print("Options:")
    print("  -h, --help              Show this help message and exit")
    print("  -v, --version           Show version and exit")
    print("  --interval-sec N        Seconds between polls (default: 300)")
    print("  --output TABLE[,TABLE]  Comma-separated tables to write.")
    print("                          Choices: usage-global, usage-users, storage-global")
    print("                          Default: all three")
    print("  --outdir DIR            Write output files to DIR (default: current directory)")
    print("  --archive               In addition to the dated files, also save a")
    print("                          timestamped copy (<datetime>.<project>.<table>.tsv)")
    print("  --append                Append rows to a persistent log file instead of")
    print("                          overwriting. Log files are named <project>.<table>.tsv")
    print("                          and the header is written only when the file is new.")
    print("                          Can be combined with --archive.")
    print("  --stdout                Print TSV to stdout instead of writing files.")
    print("                          Each poll is preceded by a '## <timestamp>' header.")
    print("                          If multiple tables are selected, each is also")
    print("                          preceded by a '## <table>' header line.")
    print("                          Implies --outdir and --archive are ignored.")
    print()
    print("Examples:")
    print("  nci-parser monitor quota -P fy54")
    print("  nci-parser monitor quota -P fy54 --interval-sec 300 --outdir /data/nci")
    print("  nci-parser monitor quota -P fy54 --output usage-global,storage-global --archive")
    print("  nci-parser monitor quota -P fy54 --stdout --output storage-global")
    print("  nci-parser monitor quota -P fy54 --append")
    print("  nci-parser monitor quota -P fy54 --append --output storage-global")
    print("  nci-parser monitor quota -P fy54 --stdout --output storage-global | csvlook -t")


def _write_tables(result, outputs, out_base, stem, label, archive_stem=None):
    """Write parsed tables to TSV files.  Returns list of (table_name, path, nrows)."""
    written = []
    for table_name in outputs:
        rows = result.get(table_name, [])
        if not rows:
            print(f"  Warning: No data for table '{table_name}' in {label}", file=sys.stderr)
            continue

        out_path = out_base / f"{stem}.{table_name}.tsv"
        try:
            with open(out_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter='\t')
                writer.writeheader()
                writer.writerows(rows)
            written.append((table_name, out_path, len(rows)))
        except Exception as e:
            print(f"  Error: Failed to write {out_path}: {e}", file=sys.stderr)

        if archive_stem:
            arch_path = out_base / f"{archive_stem}.{table_name}.tsv"
            try:
                with open(arch_path, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter='\t')
                    writer.writeheader()
                    writer.writerows(rows)
            except Exception as e:
                print(f"  Warning: Failed to write archive {arch_path}: {e}", file=sys.stderr)

    return written


def _append_tables(result, outputs, out_base, project):
    """Append parsed rows to persistent log files, writing the header only for new/empty files.
    Returns list of (table_name, path, nrows).
    """
    appended = []
    for table_name in outputs:
        rows = result.get(table_name, [])
        if not rows:
            print(f"  Warning: No data for table '{table_name}'", file=sys.stderr)
            continue
        out_path = out_base / f"{project}.{table_name}.tsv"
        write_header = not out_path.exists() or out_path.stat().st_size == 0
        try:
            with open(out_path, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter='\t')
                if write_header:
                    writer.writeheader()
                writer.writerows(rows)
            appended.append((table_name, out_path, len(rows)))
        except Exception as e:
            print(f"  Error: Failed to append to {out_path}: {e}", file=sys.stderr)
    return appended


def _print_tables_stdout(result, outputs, poll_time):
    """Print parsed tables to stdout with timestamp + optional table headers."""
    print(f"## {poll_time}")
    for table_name in outputs:
        rows = result.get(table_name, [])
        if not rows:
            print(f"## {table_name}: (no data)", file=sys.stderr)
            continue
        if len(outputs) > 1:
            print(f"## {table_name}")
        writer = csv.DictWriter(sys.stdout, fieldnames=rows[0].keys(),
                                delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    sys.stdout.flush()


def _poll_once(project, outputs, out_base, archive, to_stdout=False, append=False):
    """Run nci_account, parse, write files (or stdout).  Returns True on success."""
    now = datetime.datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    dt_str = now.strftime('%Y-%m-%dT%H%M%S')
    poll_time = now.strftime('%Y-%m-%d %H:%M:%S')
    stem = f"{date_str}.{project}"
    archive_stem = f"{dt_str}.{project}" if archive else None

    cmd = ['nci_account', '-v', '-P', project]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        print("  Error: 'nci_account' not found. Is it installed and on your PATH?",
              file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        print("  Error: 'nci_account' timed out after 60 seconds.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  Error running nci_account: {e}", file=sys.stderr)
        return False

    if result.returncode != 0:
        print(f"  Error: nci_account exited with code {result.returncode}", file=sys.stderr)
        if result.stderr:
            print(f"  stderr: {result.stderr.strip()}", file=sys.stderr)
        return False

    text = result.stdout
    try:
        parsed = parse_quota_text(text)
    except Exception as e:
        print(f"  Error: Failed to parse nci_account output: {e}", file=sys.stderr)
        return False

    # Prepend polled_at timestamp to every row in every table
    for table_name in parsed:
        parsed[table_name] = [{'polled_at': poll_time, **row}
                               for row in parsed[table_name]]

    label = f"nci_account -v -P {project}"

    if to_stdout:
        _print_tables_stdout(parsed, outputs, poll_time)
        return True

    if append:
        written = _append_tables(parsed, outputs, out_base, project)
        for table_name, out_path, nrows in written:
            print(f"  [{poll_time}]  {table_name:20s}  {nrows:4d} rows  →  {out_path} (appended)",
                  file=sys.stderr)
        if archive_stem:
            _write_tables(parsed, outputs, out_base, archive_stem, label)
        return bool(written)

    written = _write_tables(parsed, outputs, out_base, stem, label, archive_stem)
    for table_name, out_path, nrows in written:
        print(f"  [{poll_time}]  {table_name:20s}  {nrows:4d} rows  →  {out_path}",
              file=sys.stderr)

    return bool(written)


def monitor_main(argv=None):
    """Entry point for the 'monitor' subcommand."""
    if argv is None:
        argv = sys.argv[2:]  # strip 'nci-parser monitor'

    if not argv or argv[0] in ['-h', '--help', 'help']:
        print_help()
        sys.exit(0)
    if argv[0] in ['-v', '--version', 'version']:
        print("NCI Parser v{}".format(__version__))
        sys.exit(0)

    args = list(argv)

    # First positional must be the monitor type
    monitor_type = args.pop(0)
    if monitor_type != 'quota':
        print(f"Error: Unknown monitor type '{monitor_type}'. Only 'quota' is supported.",
              file=sys.stderr)
        sys.exit(1)

    # Defaults
    project = None
    interval = 300
    outputs = list(VALID_OUTPUTS)
    outdir = Path('.')
    archive = False
    append = False
    to_stdout = False

    # Parse options
    while args:
        opt = args[0]
        if opt in ['-h', '--help']:
            print_help()
            sys.exit(0)
        elif opt in ['-v', '--version']:
            print("NCI Parser v{}".format(__version__))
            sys.exit(0)
        elif opt in ['-P', '--project']:
            if len(args) < 2:
                print(f"Error: {opt} requires a value", file=sys.stderr)
                sys.exit(1)
            project = args[1]
            args = args[2:]
        elif opt == '--interval-sec':
            if len(args) < 2:
                print("Error: --interval-sec requires a value", file=sys.stderr)
                sys.exit(1)
            try:
                interval = int(args[1])
                if interval <= 0:
                    raise ValueError
            except ValueError:
                print("Error: --interval-sec must be a positive integer", file=sys.stderr)
                sys.exit(1)
            args = args[2:]
        elif opt == '--output':
            if len(args) < 2:
                print("Error: --output requires a value", file=sys.stderr)
                sys.exit(1)
            requested = [o.strip() for o in args[1].split(',')]
            invalid = [o for o in requested if o not in VALID_OUTPUTS]
            if invalid:
                print(f"Error: Unknown output table(s): {', '.join(invalid)}", file=sys.stderr)
                print(f"Valid choices: {', '.join(VALID_OUTPUTS)}", file=sys.stderr)
                sys.exit(1)
            outputs = requested
            args = args[2:]
        elif opt == '--outdir':
            if len(args) < 2:
                print("Error: --outdir requires a value", file=sys.stderr)
                sys.exit(1)
            outdir = Path(args[1])
            args = args[2:]
        elif opt == '--archive':
            archive = True
            args = args[1:]
        elif opt == '--append':
            append = True
            args = args[1:]
        elif opt == '--stdout':
            to_stdout = True
            args = args[1:]
        else:
            print(f"Error: Unknown option '{opt}'", file=sys.stderr)
            sys.exit(1)

    if not project:
        print("Error: -P / --project is required", file=sys.stderr)
        print("Run 'nci-parser monitor --help' for usage.", file=sys.stderr)
        sys.exit(1)

    if not to_stdout:
        outdir.mkdir(parents=True, exist_ok=True)
        mode = "append" if append else "overwrite"
        print(f"Monitoring project '{project}' every {interval}s  [{mode}]  →  {outdir.resolve()}",
              file=sys.stderr)
    else:
        print(f"Monitoring project '{project}' every {interval}s  →  stdout",
              file=sys.stderr)
    print("Press Ctrl+C to stop.", file=sys.stderr)

    try:
        while True:
            _poll_once(project, outputs, outdir, archive, to_stdout=to_stdout, append=append)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    monitor_main()
