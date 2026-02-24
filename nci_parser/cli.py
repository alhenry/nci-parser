#!/usr/bin/env python
"""Top-level dispatcher for the nci-parser command."""

import sys

from . import __version__
from .jobs_cli import jobs_main
from .quota_cli import quota_main


_SUBCOMMANDS = {
    'jobs':  jobs_main,
    'quota': quota_main,
}


def print_help():
    print("NCI Parser v{}".format(__version__))
    print()
    print("Usage: nci-parser <subcommand> [OPTIONS] ...")
    print()
    print("Subcommands:")
    print("  jobs   Parse NCI PBS job output files into CSV")
    print("  quota  Parse NCI account/quota reports into TSV")
    print()
    print("Options:")
    print("  -h, --help     Show this help message and exit")
    print("  -v, --version  Show version and exit")
    print()
    print("Run 'nci-parser <subcommand> --help' for subcommand-specific help.")
    print()
    print("Examples:")
    print("  nci-parser jobs results.csv job_logs/*.OU")
    print("  nci-parser quota report.txt")
    print("  nci-parser quota --output usage-users report.txt")


def main():
    """Top-level entry point."""
    args = sys.argv[1:]

    if not args or args[0] in ['-h', '--help', 'help']:
        print_help()
        sys.exit(0)

    if args[0] in ['-v', '--version', 'version']:
        print("NCI Parser v{}".format(__version__))
        sys.exit(0)

    subcommand = args[0]
    if subcommand not in _SUBCOMMANDS:
        print(f"Error: Unknown subcommand '{subcommand}'", file=sys.stderr)
        print(f"Valid subcommands: {', '.join(_SUBCOMMANDS)}", file=sys.stderr)
        print("Run 'nci-parser --help' for usage.", file=sys.stderr)
        sys.exit(1)

    # Pass remaining args to the subcommand (sys.argv[2:] is read inside each)
    _SUBCOMMANDS[subcommand]()


if __name__ == "__main__":
    main()
