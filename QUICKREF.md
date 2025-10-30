# NCI Job Parser - Quick Reference

## Basic Usage

```bash
# Parse files from command line
nci-job-parser output.csv file1.OU file2.OU file3.OU

# Parse all files in directory
nci-job-parser output.csv job_logs/*.OU

# Parse with wildcard
nci-job-parser output.csv /path/to/logs/**/*.OU
```

## Options

| Option | Description | Example |
|--------|-------------|---------|
| `--workers N` | Set number of parallel workers | `nci-job-parser --workers 8 output.csv *.OU` |
| `--no-parallel` | Disable parallel processing | `nci-job-parser --no-parallel output.csv *.OU` |
| `--file-list FILE` | Read file paths from FILE | `nci-job-parser output.csv --file-list files.txt` |
| `-` | Read file paths from stdin | `find . -name "*.OU" \| nci-job-parser output.csv -` |

## Input Methods

### 1. Command Line Arguments (default)
```bash
nci-job-parser output.csv file1.OU file2.OU file3.OU
```

### 2. File List
Create a text file with one file path per line:
```
# files.txt
job_logs/142112589.gadi-pbs.OU
job_logs/142208190.gadi-pbs.OU
```

Then use:
```bash
nci-job-parser output.csv --file-list files.txt
```

### 3. Standard Input (stdin)
Pipe file paths from other commands:
```bash
find job_logs -name "*.OU" | nci-job-parser output.csv -
```

## Common Workflows

### Find jobs from last week
```bash
find /path/to/logs -name "*.OU" -mtime -7 | nci-job-parser recent.csv -
```

### Find failed jobs (exit status != 0)
```bash
grep -l "Exit Status.*[^0]" *.OU | nci-job-parser failed.csv -
```

### Find jobs using > 100GB memory
```bash
grep -l "Memory Used.*[1-9][0-9][0-9]\.[0-9]*GB" *.OU | nci-job-parser highmem.csv -
```

### Process specific project
```bash
grep -l "Project.*fy54" *.OU | nci-job-parser fy54_jobs.csv -
```

### Combine multiple searches
```bash
# Create file list with multiple criteria
find /logs -name "*.OU" -mtime -30 > recent.txt
grep -l "Project.*fy54" recent.txt > fy54_recent.txt
nci-job-parser output.csv --file-list fy54_recent.txt
```

## Performance Tips

1. **Use parallel processing** (default) for large batches
2. **Use stdin** (`-`) when filtering with other tools
3. **Use file lists** for complex multi-stage selections
4. **Adjust workers** based on I/O vs CPU workload:
   - Local files: Use default (CPU count)
   - Network files: Reduce workers to avoid I/O bottleneck
   - SSD: Can use more workers than CPU count

## Output

The tool creates a CSV file with columns:

- `filename` - Original filename
- `usage_date` - Date of resource usage report
- `usage_time` - Time of resource usage report  
- `Job Id` - PBS job ID
- `Project` - NCI project code
- `Exit Status` - Job exit status (0 = success)
- `Service Units` - SU consumed
- `NCPUs Requested` - Requested CPUs
- `NCPUs Used` - Actually used CPUs
- `CPU Time Used` - Total CPU time (HH:MM:SS)
- `Memory Requested` - Requested memory
- `Memory Used` - Actually used memory
- `Walltime requested` - Requested walltime
- `Walltime Used` - Actually used walltime
- `JobFS requested` - Requested JobFS space
- `JobFS used` - Actually used JobFS space

## Troubleshooting

### No files found
```bash
# Check your file paths are correct
ls examples/*.OU

# Use absolute paths
nci-job-parser output.csv /full/path/to/examples/*.OU
```

### Files not parsing
```bash
# Check if files have resource usage section
tail -20 file.OU

# Try with --no-parallel for better error messages
nci-job-parser --no-parallel output.csv file.OU
```

### Slow performance
```bash
# Increase workers
nci-job-parser --workers 16 output.csv *.OU

# Check if parallel is enabled (default)
# Look for "Using N worker(s)" message
```

### Memory issues with very large batches
```bash
# Process in smaller chunks
find logs/ -name "*.OU" | split -l 10000 - chunk_
for f in chunk_*; do
  nci-job-parser batch_$(basename $f).csv --file-list $f
done
```
