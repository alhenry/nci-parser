#!/usr/bin/env python
"""Quota subcommand — parse NCI account/quota output files into TSV."""

import csv
import sys
from pathlib import Path

from .quota_parser import parse_quota_file, parse_quota_text, VALID_OUTPUTS
from . import __version__


def print_help():
    print("NCI Parser v{}  —  quota subcommand".format(__version__))
    print()
    print("Usage: nci-parser quota [OPTIONS] [<input_file>]")
    print()
    print("Parse an NCI account/quota report and write tab-delimited output files.")
    print("By default all three tables are written.")
    print()
    print("Input can be a file path, '-' for stdin, or omitted to read from stdin.")
    print("This allows piping directly: nci-account -v -P <project> | nci-parser quota")
    print()
    print("Output files are written alongside the input file (or to --outdir).")
    print("When reading from stdin, --outdir must be specified or output goes to stdout.")
    print("  <stem>.usage-global.tsv   — overall usage summary + stakeholder breakdown")
    print("  <stem>.usage-users.tsv    — per-user usage and reserved amounts")
    print("  <stem>.storage-global.tsv — per-filesystem storage usage + stakeholders")
    print()
    print("Options:")
    print("  -h, --help              Show this help message and exit")
    print("  -v, --version           Show version and exit")
    print("  --output TABLE[,TABLE]  Comma-separated list of tables to write.")
    print("                          Choices: usage-global, usage-users, storage-global")
    print("                          Default: all three")
    print("  --outdir DIR            Write output files to DIR instead of alongside input")
    print("  --stem NAME             Base filename stem when reading from stdin")
    print("                          Default: 'stdin'")
    print("  --stdout                Print TSV output to stdout instead of writing files.")
    print("                          Use --output to select a single table (recommended).")
    print("                          If multiple tables are selected, each is preceded by")
    print("                          a '## <table>' header line.")
    print()
    print("Examples:")
    print("  nci-parser quota report.txt")
    print("  nci-parser quota --output usage-users report.txt")
    print("  nci-parser quota --output usage-global,storage-global report.txt")
    print("  nci-parser quota --outdir results/ report.txt")
    print("  nci-account -v -P ab12 | nci-parser quota --outdir results/")
    print("  nci-account -v -P ab12 | nci-parser quota --outdir results/ --stem ab12")
    print("  nci-account -v -P ab12 | nci-parser quota --stdout --output usage-users")
    print("  nci-account -v -P ab12 | nci-parser quota --stdout --output usage-global | csvlook -t")


def print_version():
    print("NCI Parser v{}".format(__version__))


def quota_main(argv=None):
    """Entry point for the 'quota' subcommand."""
    if argv is None:
        argv = sys.argv[2:]  # strip 'nci-parser quota'

    if not argv or argv[0] in ['-h', '--help', 'help']:
        print_help()
        sys.exit(0 if (not argv or argv[0] in ['-h', '--help', 'help']) else 1)
    if argv[0] in ['-v', '--version', 'version']:
        print_version()
        sys.exit(0)

    args = list(argv)
    outputs = list(VALID_OUTPUTS)   # default: all three
    outdir = None
    stem_override = None
    to_stdout = False

    # Parse options
    while args and args[0].startswith('-'):
        opt = args[0]
        if opt in ['-h', '--help']:
            print_help()
            sys.exit(0)
        elif opt in ['-v', '--version']:
            print_version()
            sys.exit(0)
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
        elif opt == '--stem':
            if len(args) < 2:
                print("Error: --stem requires a value", file=sys.stderr)
                sys.exit(1)
            stem_override = args[1]
            args = args[2:]
        elif opt == '--stdout':
            to_stdout = True
            args = args[1:]
        elif opt == '-':
            break  # treat '-' as the positional stdin argument
        else:
            print(f"Error: Unknown option {opt}", file=sys.stderr)
            sys.exit(1)

    # Determine input source: file path, '-', or stdin if no positional arg
    from_stdin = False
    if not args or args[0] == '-':
        from_stdin = True
        input_path = None
    else:
        if len(args) > 1:
            print(f"Error: Expected exactly one input file, got {len(args)}", file=sys.stderr)
            sys.exit(1)
        input_path = Path(args[0])
        if not input_path.exists():
            print(f"Error: Input file not found: {input_path}", file=sys.stderr)
            sys.exit(1)

    # Read input
    try:
        if from_stdin:
            text = sys.stdin.read()
        else:
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as fh:
                text = fh.read()
    except Exception as e:
        src = 'stdin' if from_stdin else input_path
        print(f"Error: Failed to read {src}: {e}", file=sys.stderr)
        sys.exit(1)

    # Parse
    try:
        result = parse_quota_text(text)
    except Exception as e:
        src = 'stdin' if from_stdin else input_path
        print(f"Error: Failed to parse {src}: {e}", file=sys.stderr)
        sys.exit(1)

    # Determine output stem and directory
    if from_stdin:
        stem = stem_override or 'stdin'
    else:
        stem = stem_override or input_path.stem

    if outdir:
        out_base = Path(outdir)
    elif from_stdin:
        out_base = Path('.')
    else:
        out_base = input_path.parent
    out_base.mkdir(parents=True, exist_ok=True)

    src_label = 'stdin' if from_stdin else input_path

    # Write requested tables
    written = []
    for table_name in outputs:
        rows = result.get(table_name, [])
        if not rows:
            print(f"Warning: No data for table '{table_name}' in {src_label}", file=sys.stderr)
            continue

        if to_stdout:
            if len(outputs) > 1:
                print(f"## {table_name}")
            writer = csv.DictWriter(sys.stdout, fieldnames=rows[0].keys(),
                                    delimiter='\t', lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
            written.append((table_name, '<stdout>', len(rows)))
        else:
            out_path = out_base / f"{stem}.{table_name}.tsv"
            try:
                with open(out_path, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter='\t')
                    writer.writeheader()
                    writer.writerows(rows)
                written.append((table_name, out_path, len(rows)))
            except Exception as e:
                print(f"Error: Failed to write {out_path}: {e}", file=sys.stderr)
                sys.exit(1)

    # Summary (always to stderr so it doesn't pollute stdout)
    for table_name, out_path, nrows in written:
        print(f"  {table_name:20s}  {nrows:4d} rows  →  {out_path}", file=sys.stderr)

    if not written:
        print("Warning: No output files written.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    quota_main()
