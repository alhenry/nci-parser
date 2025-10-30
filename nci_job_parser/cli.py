#!/usr/bin/env python
"""Command-line interface for NCI Job Parser."""

import csv
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count

from .parser import parse_file_tail


def process_single_file(filepath):
    """
    Process a single file and return the parsed data.
    
    Args:
        filepath: Path to file to process
        
    Returns:
        Tuple of (filename, parsed_data) or (filename, None) on error
    """
    try:
        row = parse_file_tail(filepath)
        if row:
            row["filename"] = Path(filepath).name
            return (filepath, row)
        else:
            return (filepath, None)
    except Exception as e:
        print(f"Warning: Error processing {filepath}: {e}", file=sys.stderr)
        return (filepath, None)


def main():
    """Main entry point for the CLI."""
    if len(sys.argv) < 2:
        print("Usage: nci-job-parser [OPTIONS] <output.csv> <file1> [<file2> ...]")
        print("       nci-job-parser [OPTIONS] <output.csv> --file-list <list.txt>")
        print("       nci-job-parser [OPTIONS] <output.csv> -")
        print("\nParse NCI job output files and write to CSV format.")
        print("\nOptions:")
        print("  --workers N      Number of parallel workers (default: CPU count)")
        print("  --no-parallel    Disable parallel processing")
        print("  --file-list FILE Read file paths from FILE (one per line)")
        print("  -                Read file paths from stdin (one per line)")
        print("\nExample:")
        print("  nci-job-parser results.csv job_logs/*.OU")
        print("  nci-job-parser --workers 8 results.csv job_logs/*.OU")
        print("  nci-job-parser results.csv --file-list files.txt")
        print("  find job_logs -name '*.OU' | nci-job-parser results.csv -")
        sys.exit(1)
    
    # Parse arguments
    args = sys.argv[1:]
    workers = cpu_count()
    use_parallel = True
    
    # Check for options at the beginning
    while args and args[0].startswith('--') and args[0] not in ['--file-list']:
        if args[0] == '--workers' and len(args) > 1:
            try:
                workers = int(args[1])
                args = args[2:]
            except ValueError:
                print("Error: --workers requires an integer value", file=sys.stderr)
                sys.exit(1)
        elif args[0] == '--no-parallel':
            use_parallel = False
            args = args[1:]
        else:
            print(f"Error: Unknown option {args[0]}", file=sys.stderr)
            sys.exit(1)
    
    if len(args) < 1:
        print("Error: Missing output file argument", file=sys.stderr)
        sys.exit(1)
    
    output_csv = args[0]
    files = []
    use_stdin = False
    
    # Process remaining arguments (files or --file-list)
    i = 1
    while i < len(args):
        if args[i] == '--file-list' and i + 1 < len(args):
            # Read file list from file
            file_list_path = args[i + 1]
            try:
                with open(file_list_path, 'r') as f:
                    file_list_files = [line.strip() for line in f if line.strip()]
                files.extend(file_list_files)
                print(f"Read {len(file_list_files)} file path(s) from {file_list_path}", file=sys.stderr)
            except Exception as e:
                print(f"Error reading file list from {file_list_path}: {e}", file=sys.stderr)
                sys.exit(1)
            i += 2
        elif args[i] == '-':
            # Read from stdin
            use_stdin = True
            i += 1
        else:
            # Regular file argument
            files.append(args[i])
            i += 1
    
    # Read file list from stdin if requested
    if use_stdin:
        try:
            stdin_files = [line.strip() for line in sys.stdin if line.strip()]
            files.extend(stdin_files)
            print(f"Read {len(stdin_files)} file path(s) from stdin", file=sys.stderr)
        except Exception as e:
            print(f"Error reading from stdin: {e}", file=sys.stderr)
            sys.exit(1)
    
    if not files:
        print("Error: No input files specified", file=sys.stderr)
        sys.exit(1)
    
    print(f"Processing {len(files)} file(s)...", file=sys.stderr)
    
    all_rows = []
    all_keys = set()
    processed = 0
    skipped = 0

    if use_parallel and len(files) > 1:
        # Parallel processing for large batches
        print(f"Using {workers} worker(s) for parallel processing", file=sys.stderr)
        
        with ProcessPoolExecutor(max_workers=workers) as executor:
            # Submit all files for processing
            future_to_file = {executor.submit(process_single_file, f): f for f in files}
            
            # Process results as they complete
            for future in as_completed(future_to_file):
                filepath, row = future.result()
                
                if row:
                    all_rows.append(row)
                    all_keys.update(row.keys())
                    processed += 1
                else:
                    skipped += 1
                    print(f"Warning: No resource usage section found in {filepath}", file=sys.stderr)
                
                # Progress indicator for large batches
                if (processed + skipped) % 100 == 0:
                    print(f"Progress: {processed + skipped}/{len(files)} files processed", file=sys.stderr)
    else:
        # Sequential processing for small batches or when parallel is disabled
        for filepath in files:
            try:
                row = parse_file_tail(filepath)
                if row:
                    row["filename"] = Path(filepath).name
                    all_rows.append(row)
                    all_keys.update(row.keys())
                    processed += 1
                else:
                    skipped += 1
                    print(f"Warning: No resource usage section found in {filepath}", file=sys.stderr)
            except Exception as e:
                skipped += 1
                print(f"Warning: Error processing {filepath}: {e}", file=sys.stderr)

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
        print(f"\nSuccessfully wrote {processed} job(s) to {output_csv}", file=sys.stderr)
        if skipped > 0:
            print(f"Skipped {skipped} file(s) due to errors or missing data", file=sys.stderr)
    except Exception as e:
        print(f"Error: Failed to write output file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
