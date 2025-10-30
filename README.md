# NCI Job Parser

A simple Python command-line tool to parse NCI (National Computational Infrastructure) job output files and extract resource usage information into tabular format (CSV).

## Features

- Extracts resource usage data from NCI PBS job output files
- Handles multiple input files
- Outputs to CSV format for easy analysis
- Preserves time format in fields like CPU Time Used, Walltime
- Extracts job metadata including Job ID, Project, Exit Status, Service Units, Memory, CPUs, etc.

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

```bash
nci-job-parser <output.csv> <file1> [<file2> ...]
```

### Example

Parse a single job output file:
```bash
nci-job-parser results.csv examples/142112589.gadi-pbs.OU
```

Parse multiple job output files:
```bash
nci-job-parser results.csv examples/*.OU
```

Parse files from a directory:
```bash
nci-job-parser output.csv /path/to/job_logs/*.OU
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
