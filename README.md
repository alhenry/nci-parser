# NCI Parser

A Python command-line tool to parse NCI (National Computational Infrastructure) output files and extract resource usage information into tabular format.

## Features

- **`jobs` subcommand** — parse PBS job output files into CSV
  - Parallel processing across multiple CPU cores
  - Optimised file reading (only reads file tails where resource data lives)
  - Accepts file lists and stdin for easy integration with `find`
- **`quota` subcommand** — parse `nci-account` quota/storage reports into TSV
  - Produces three tables: overall usage, per-user usage, and storage
  - Reads from a file, stdin (pipe directly from `nci-account`), or `-`
  - Write output to files or print to stdout for further processing

## Performance

The `jobs` subcommand is optimised for large batches:

- **Parallel processing**: uses multiple CPU cores concurrently
- **Line-based tail reading**: only reads the last 30 lines of each file
- **Compiled regex**: pre-compiled patterns for faster parsing
- Typical performance: ~1 000 files in under 10 s, ~10 000 files in under 60 s (8-core machine)

See [PERFORMANCE.md](PERFORMANCE.md) for benchmarks and [QUICKREF.md](QUICKREF.md) for a quick reference guide.

## Installation

```bash
git clone https://github.com/alhenry/nci-parser.git
cd nci-parser
pip install -e .
```

## Usage

```
nci-parser <subcommand> [OPTIONS] ...
```

Run `nci-parser --help` for top-level help, or `nci-parser <subcommand> --help` for subcommand-specific help.

---

### `jobs` — Parse PBS job output files

```
nci-parser jobs [OPTIONS] <output.csv> <file1> [<file2> ...]
nci-parser jobs [OPTIONS] <output.csv> --file-list <list.txt>
nci-parser jobs [OPTIONS] <output.csv> -
```

**Options:**

| Option | Description |
|---|---|
| `-h, --help` | Show help and exit |
| `-v, --version` | Show version and exit |
| `--workers N` | Number of parallel workers (default: CPU count) |
| `--no-parallel` | Disable parallel processing |
| `--file-list FILE` | Read file paths from FILE (one per line) |
| `-` | Read file paths from stdin (one per line) |

**Examples:**

```bash
# Parse files directly
nci-parser jobs results.csv job_logs/*.OU

# Use a specific number of workers
nci-parser jobs --workers 8 results.csv job_logs/*.OU

# Parse from a file list
nci-parser jobs results.csv --file-list files.txt

# Pipe from find
find /path/to/job_logs -name "*.OU" -mtime -7 | nci-parser jobs recent_jobs.csv -
```

**Output columns:**

`filename`, `usage_date`, `usage_time`, `Job Id`, `Project`, `Exit Status`, `Service Units`, `NCPUs Requested`, `NCPUs Used`, `CPU Time Used`, `Memory Requested`, `Memory Used`, `Walltime requested`, `Walltime Used`, `JobFS requested`, `JobFS used`

**Expected input format:**

```
======================================================================================
                  Resource Usage on 2025-06-02 00:24:42:
   Job Id:             142112589.gadi-pbs
   Project:            ei56
   Exit Status:        0
   Service Units:      639.55
   NCPUs Requested:    16                     NCPUs Used: 16
                                           CPU Time Used: 11:21:45
   Memory Requested:   600.0GB               Memory Used: 491.87GB
   Walltime requested: 12:00:00            Walltime Used: 11:22:11
   JobFS requested:    500.0MB                JobFS used: 0B
======================================================================================
```

---

### `quota` — Parse NCI account/quota reports

```
nci-parser quota [OPTIONS] [<input_file>]
```

Input can be a file path, `-` for stdin, or omitted to read from stdin — allowing direct piping from `nci-account`.

**Options:**

| Option | Description |
|---|---|
| `-h, --help` | Show help and exit |
| `-v, --version` | Show version and exit |
| `--output TABLE[,TABLE]` | Tables to write: `usage-global`, `usage-users`, `storage-global` (default: all three) |
| `--outdir DIR` | Write output files to DIR instead of alongside the input file |
| `--stem NAME` | Base filename stem when reading from stdin (default: `stdin`) |
| `--stdout` | Print TSV to stdout instead of writing files |

**Output tables:**

| Table | Filename | Description |
|---|---|---|
| `usage-global` | `<stem>.usage-global.tsv` | Overall compute usage + stakeholder breakdown |
| `usage-users` | `<stem>.usage-users.tsv` | Per-user usage and reserved amounts |
| `storage-global` | `<stem>.storage-global.tsv` | Per-filesystem storage usage + stakeholder breakdown |

**Examples:**

```bash
# Parse a saved report file
nci-parser quota report.txt

# Write output to a specific directory
nci-parser quota --outdir results/ report.txt

# Select a single table
nci-parser quota --output usage-users report.txt

# Pipe directly from nci-account
nci-account -v -P ab12 | nci-parser quota --outdir results/ --stem ab12

# Print a single table to stdout (e.g. for further processing)
nci-account -v -P ab12 | nci-parser quota --stdout --output usage-users

# Pipe into column for pretty printing
nci-account -v -P ab12 | nci-parser quota --stdout --output usage-global | column -t -s $'\t'
```

## License

MIT License

