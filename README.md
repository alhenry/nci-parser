# NCI Job Parser

A simple Python command-line tool to parse NCI (National Computational Infrastructure) job output files and extract resource usage information into tabular format (CSV).

## Features

- Extracts resource usage data from NCI PBS job output files
- Handles multiple input files efficiently
- **Parallel processing** for fast handling of thousands of files
- **Optimized file reading** - only reads file tails where resource data is located
- Outputs to CSV format for easy analysis
- Preserves time format in fields like CPU Time Used, Walltime
- Extracts job metadata including Job ID, Project, Exit Status, Service Units, Memory, CPUs, etc.

## Performance

The parser is optimized for processing large numbers of files:

- **Parallel Processing**: Uses multiple CPU cores to process files concurrently
- **Line-based Tail Reading**: Only reads the last 30 lines of each file (where resource usage is located) instead of entire files
- **Compiled Regex**: Pre-compiled regex patterns for faster parsing
- **Progress Indicators**: Shows progress when processing large batches (every 100 files)
- **Flexible Input**: Supports file lists and stdin for easy integration with `find` and other tools

Typical performance:
- ~1000 files in under 10 seconds (on 8-core machine)
- ~10000 files in under 60 seconds (on 8-core machine)

For detailed performance information and benchmarks, see [PERFORMANCE.md](PERFORMANCE.md).

For a quick reference guide with common workflows, see [QUICKREF.md](QUICKREF.md).

## Installation

### From source

```bash
git clone https://github.com/alhenry/nci-job-parser.git
cd nci-job-parser
pip install -e .
```

### Development installation

```bash
pip install -e .
```

## Usage

### Command Line

Basic usage:
```bash
nci-job-parser <output.csv> <file1> [<file2> ...]
```

With options:
```bash
nci-job-parser [OPTIONS] <output.csv> <file1> [<file2> ...]
```

**Options:**
- `-h, --help` - Show help message and exit
- `-v, --version` - Show version and exit
- `--workers N` - Number of parallel workers (default: CPU count)
- `--no-parallel` - Disable parallel processing (useful for debugging)
- `--file-list FILE` - Read file paths from FILE (one per line)
- `-` - Read file paths from stdin (one per line)

### Example

Show help and version:
```bash
nci-job-parser --help
nci-job-parser --version
```

Parse files directly from command line:
```bash
nci-job-parser results.csv examples/*.OU
```

Parse multiple job output files:
```bash
nci-job-parser results.csv examples/*.OU
```

Parse files from a directory using shell globbing:
```bash
nci-job-parser output.csv /path/to/job_logs/*.OU
```

Parse using a file list:
```bash
nci-job-parser output.csv --file-list files.txt
```

Parse using `find` and stdin (useful for complex searches):
```bash
find /path/to/job_logs -name "*.OU" -mtime -7 | nci-job-parser recent_jobs.csv -
```

Parse with a specific number of workers:
```bash
nci-job-parser --workers 16 output.csv /path/to/job_logs/*.OU
```

Combine options:
```bash
find /path/to/job_logs -name "*.OU" | nci-job-parser --workers 16 output.csv -
```

### Output

The tool generates a CSV file with columns for each resource metric found in the job output files:

| filename | usage_date | usage_time | Job Id | Project | Exit Status | Service Units | NCPUs Requested | NCPUs Used | CPU Time Used | Memory Requested | Memory Used | Walltime requested | Walltime Used | JobFS requested | JobFS used |
|----------|------------|------------|--------|---------|-------------|---------------|-----------------|------------|---------------|------------------|-------------|-------------------|---------------|-----------------|------------|
| 142112589.gadi-pbs.OU | 2025-06-02 | 00:24:42 | 142112589.gadi-pbs | ei56 | 0 | 639.55 | 16 | 16 | 11:21:45 | 600.0GB | 491.87GB | 12:00:00 | 11:22:11 | 500.0MB | 0B |

## Input Format

The tool expects NCI PBS job output files that contain a resource usage section at the end, formatted like:

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

## License

MIT License
Utility program to parse NCI job output
