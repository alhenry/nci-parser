#!/usr/bin/env python
"""Command-line interface for NCI Job Parser."""

import csv
import sys
from pathlib import Path

from .parser import parse_resource_usage_section


def main():
    """Main entry point for the CLI."""
    if len(sys.argv) < 3:
        print("Usage: nci-job-parser <output.csv> <file1> [<file2> ...]")
        print("\nParse NCI job output files and write to CSV format.")
        print("\nExample:")
        print("  nci-job-parser results.csv job_logs/*.OU")
        sys.exit(1)
    
    output_csv = sys.argv[1]
    files = sys.argv[2:]
    
    all_rows = []
    all_keys = set()

    for file in files:
        try:
            with open(file, "r") as f:
                text = f.read()
        except FileNotFoundError:
            print(f"Warning: File not found: {file}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"Warning: Error reading {file}: {e}", file=sys.stderr)
            continue
            
        row = parse_resource_usage_section(text)
        if row:
            row["filename"] = Path(file).name
            all_rows.append(row)
            all_keys.update(row.keys())
        else:
            print(f"Warning: No resource usage section found in {file}", file=sys.stderr)

    if not all_rows:
        print("Error: No valid job output files found.", file=sys.stderr)
        sys.exit(1)

    # Order columns: filename first, then sorted
    all_keys = ["filename"] + sorted(k for k in all_keys if k != "filename")
    
    try:
        with open(output_csv, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=all_keys, delimiter=",")
            writer.writeheader()
            for row in all_rows:
                writer.writerow(row)
        print(f"Successfully wrote {len(all_rows)} job(s) to {output_csv}")
    except Exception as e:
        print(f"Error: Failed to write output file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
