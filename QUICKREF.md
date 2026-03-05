# NCI Parser - Quick Reference

## Subcommands

| Subcommand | Description |
|---|---|
| `jobs` | Parse PBS job output files into CSV |
| `quota` | Parse `nci-account` quota/storage reports into TSV |
| `monitor` | Continuously poll `nci_account` and keep TSV output up to date |

```bash
nci-parser --help
nci-parser <subcommand> --help
```

---

## `jobs` — Parse PBS job output files

### Basic Usage

```bash
# Parse files from command line
nci-parser jobs output.csv file1.OU file2.OU file3.OU

# Parse all files in directory
nci-parser jobs output.csv job_logs/*.OU

# Parse with wildcard
nci-parser jobs output.csv /path/to/logs/**/*.OU
```

### Options

| Option | Description | Example |
|--------|-------------|---------|
| `-h, --help` | Show help message | `nci-parser jobs --help` |
| `-v, --version` | Show version | `nci-parser --version` |
| `--workers N` | Set number of parallel workers | `nci-parser jobs --workers 8 output.csv *.OU` |
| `--no-parallel` | Disable parallel processing | `nci-parser jobs --no-parallel output.csv *.OU` |
| `--file-list FILE` | Read file paths from FILE | `nci-parser jobs output.csv --file-list files.txt` |
| `-` | Read file paths from stdin | `find . -name "*.OU" \| nci-parser jobs output.csv -` |

### Input Methods

#### 1. Command Line Arguments (default)
```bash
nci-parser jobs output.csv file1.OU file2.OU file3.OU
```

#### 2. File List
Create a text file with one file path per line:
```
# files.txt
job_logs/142112589.gadi-pbs.OU
job_logs/142208190.gadi-pbs.OU
```

Then use:
```bash
nci-parser jobs output.csv --file-list files.txt
```

#### 3. Standard Input (stdin)
Pipe file paths from other commands:
```bash
find job_logs -name "*.OU" | nci-parser jobs output.csv -
```

### Common Workflows

```bash
# Find jobs from last week
find /path/to/logs -name "*.OU" -mtime -7 | nci-parser jobs recent.csv -

# Find failed jobs (exit status != 0)
grep -l "Exit Status.*[^0]" *.OU | nci-parser jobs failed.csv -

# Find jobs using > 100GB memory
grep -l "Memory Used.*[1-9][0-9][0-9]\.[0-9]*GB" *.OU | nci-parser jobs highmem.csv -

# Process specific project
grep -l "Project.*fy54" *.OU | nci-parser jobs fy54_jobs.csv -

# Process in chunks for very large batches
find logs/ -name "*.OU" | split -l 10000 - chunk_
for f in chunk_*; do
  nci-parser jobs batch_$(basename $f).csv --file-list $f
done
```

### Performance Tips

1. **Use parallel processing** (default) for large batches
2. **Use stdin** (`-`) when filtering with other tools
3. **Use file lists** for complex multi-stage selections
4. **Adjust workers** based on I/O vs CPU workload:
   - Local files: use default (CPU count)
   - Network files: reduce workers to avoid I/O bottleneck

### Output columns

`filename`, `usage_date`, `usage_time`, `Job Id`, `Project`, `Exit Status`, `Service Units`, `NCPUs Requested`, `NCPUs Used`, `CPU Time Used`, `Memory Requested`, `Memory Used`, `Walltime requested`, `Walltime Used`, `JobFS requested`, `JobFS used`

### Troubleshooting

```bash
# Check file paths are correct
ls examples/*.OU

# Check a file has a resource usage section
tail -20 file.OU

# Use --no-parallel for clearer error messages
nci-parser jobs --no-parallel output.csv file.OU

# Increase workers for large batches
nci-parser jobs --workers 16 output.csv *.OU
```

---

## `quota` — Parse NCI account/quota reports

### Basic Usage

```bash
# Parse a saved report file (writes TSV files alongside the input)
nci-parser quota report.txt

# Write output to a specific directory
nci-parser quota --outdir results/ report.txt

# Pipe directly from nci-account
nci-account -v -P fy54 | nci-parser quota --outdir results/ --stem fy54
```

### Options

| Option | Description |
|---|---|
| `-h, --help` | Show help and exit |
| `--output TABLE[,TABLE]` | Tables to write: `usage-global`, `usage-users`, `storage-global` (default: all three) |
| `--outdir DIR` | Write output files to DIR instead of alongside the input file |
| `--stem NAME` | Base filename stem when reading from stdin (default: `stdin`) |
| `--stdout` | Print TSV to stdout instead of writing files |

### Output tables

| Table | Filename | Description |
|---|---|---|
| `usage-global` | `<stem>.usage-global.tsv` | Overall compute usage + stakeholder breakdown |
| `usage-users` | `<stem>.usage-users.tsv` | Per-user usage and reserved amounts |
| `storage-global` | `<stem>.storage-global.tsv` | Per-filesystem storage usage + stakeholder breakdown |

### Common Workflows

```bash
# Select a single table
nci-parser quota --output usage-users report.txt

# Pipe output to column for pretty printing
nci-account -v -P fy54 | nci-parser quota --stdout --output usage-global | column -t -s $'\t'

# Pipe output to csvlook
nci-account -v -P fy54 | nci-parser quota --stdout --output storage-global | csvlook -t
```

---

## `monitor` — Continuously poll NCI account data

### Basic Usage

```bash
# Poll every 5 minutes (default), write TSV files to current directory
nci-parser monitor quota -P fy54

# Poll every 60 seconds, write to a specific directory
nci-parser monitor quota -P fy54 --interval-sec 60 --outdir /data/nci
```

### Options

| Option | Description |
|---|---|
| `-h, --help` | Show help and exit |
| `-P, --project ID` | NCI project identifier (required) |
| `--interval-sec N` | Seconds between polls (default: `300`) |
| `--output TABLE[,TABLE]` | Tables to write (default: all three) |
| `--outdir DIR` | Write output files to DIR (default: current directory) |
| `--archive` | Also save a timestamped copy on each poll |
| `--stdout` | Stream TSV to stdout instead of writing files |

### Common Workflows

```bash
# Only track storage usage, keep an archive of every snapshot
nci-parser monitor quota -P fy54 --output storage-global --archive

# Stream live storage table to stdout
nci-parser monitor quota -P fy54 --stdout --output storage-global

# Pretty-print live table in the terminal
nci-parser monitor quota -P fy54 --stdout --output storage-global | csvlook -t

# Stream to stdout and also tee to a file
nci-parser monitor quota -P fy54 --stdout --output usage-global | tee usage.tsv
```

> **Note:** `nci_account` must be available on your `PATH` (installed as part of the NCI environment on Gadi).
