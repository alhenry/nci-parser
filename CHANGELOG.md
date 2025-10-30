# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2025-10-30

### Added
- **Line-based tail reading**: More efficient - reads only last 30 lines instead of last N bytes
- **File list support**: `--file-list` option to read file paths from a file
- **Stdin support**: `-` option to read file paths from stdin for pipeline integration
- **Help flag**: `-h, --help` to show help message
- **Version flag**: `-v, --version` to show version information
- Better integration with Unix tools like `find`

### Changed
- Improved tail reading algorithm: line-based instead of byte-based
- Resource usage section is always within last 20-25 lines, optimized for this
- More flexible input methods (direct args, file list, or stdin)
- Enhanced help output with usage examples

### Example Use Cases
```bash
# Using file list
nci-job-parser output.csv --file-list files.txt

# Using find with stdin
find /path/to/logs -name "*.OU" -mtime -7 | nci-job-parser recent.csv -

# Combined with other Unix tools
grep -l "Exit Status.*0" *.OU | nci-job-parser successful.csv -
```

## [0.2.0] - 2025-10-30

### Added
- **Parallel processing** support using multiprocessing for faster handling of thousands of files
- **Optimized file reading** - only reads file tails (~8KB) where resource usage data is located
- Command-line options:
  - `--workers N` to control number of parallel workers
  - `--no-parallel` to disable parallel processing
- Progress indicators for large batches (shows progress every 100 files)
- Performance benchmark script (`benchmark.py`)
- Better error handling and reporting

### Changed
- Improved performance for processing large numbers of files:
  - ~10-20% faster for individual file parsing (tail reading)
  - ~N× faster for batch processing where N = CPU cores (parallel processing)
- More informative output messages (shows processed/skipped counts)
- Pre-compiled regex patterns for better performance

### Fixed
- Memory efficiency when processing very large files
- Better handling of encoding errors in input files

## [0.1.0] - 2025-10-30

### Added
- Initial release
- Parse NCI PBS job output files for resource usage information
- Extract fields: Job ID, Project, Exit Status, Service Units, CPUs, Memory, Walltime, JobFS
- Support for time values in fields (e.g., CPU Time Used)
- CSV output format
- Command-line interface
- Installable package with `pip`
- Comprehensive README with examples
