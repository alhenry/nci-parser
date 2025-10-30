# nci-job-parser

A simple Python parser to parse job submission output from Australia's National Computing Infrastructure (NCI) and write the information into a tabular file format.

## Description

This utility parses NCI job submission output (typically from PBS/Torque batch systems) and extracts job information into structured formats (CSV or TSV). It can handle various job output formats including:

- Simple job IDs: `12345678`
- Full job IDs with server: `12345678.gadi-pbs`
- Job submission messages: `Job 12345678.gadi-pbs submitted`
- Job queued messages: `Job 12345678.gadi-pbs queued`

## Installation

No external dependencies required! The parser uses only Python standard library.

Simply clone this repository:

```bash
git clone https://github.com/alhenry/nci-job-parser.git
cd nci-job-parser
```

## Usage

### Command Line Interface

```bash
python3 nci_job_parser.py <input_file> <output_file> [-f {csv,tsv}]
```

#### Arguments:

- `input_file`: Path to the input file containing NCI job submission output
- `output_file`: Path to the output file where parsed data will be written
- `-f, --format`: Output format (csv or tsv), default is csv

### Examples

#### Parse job output to CSV:

```bash
python3 nci_job_parser.py examples/sample_job_output.txt output.csv
```

#### Parse job output to TSV:

```bash
python3 nci_job_parser.py examples/sample_job_output.txt output.tsv -f tsv
```

### Sample Input

```
12345678.gadi-pbs
Job 12345679.gadi-pbs submitted
87654321.gadi-pbs
Job 11111111.gadi-pbs submitted
22222222.gadi-pbs
```

### Sample Output (CSV)

```csv
line_number,job_id,job_id_full,server,status
1,12345678,12345678.gadi-pbs,gadi-pbs,submitted
2,12345679,12345679.gadi-pbs,gadi-pbs,submitted
3,87654321,87654321.gadi-pbs,gadi-pbs,submitted
4,11111111,11111111.gadi-pbs,gadi-pbs,submitted
5,22222222,22222222.gadi-pbs,gadi-pbs,submitted
```

## Output Fields

The parser extracts the following information:

- `line_number`: Line number in the input file where the job was found
- `job_id`: Numeric job ID
- `job_id_full`: Full job ID including server name (if present)
- `server`: Server/queue name (e.g., gadi-pbs)
- `status`: Job status (submitted/queued)

## Using as a Library

You can also use the parser as a Python library:

```python
from nci_job_parser import NCIJobParser
from pathlib import Path

# Create parser instance
parser = NCIJobParser()

# Parse a file
jobs = parser.parse_file(Path('job_output.txt'))

# Or parse text directly
text = "12345678.gadi-pbs\nJob 87654321.gadi-pbs submitted"
jobs = parser.parse_text(text)

# Write to CSV
parser.write_csv(jobs, Path('output.csv'))

# Write to TSV
parser.write_tsv(jobs, Path('output.tsv'))
```

## Testing

Run the test suite:

```bash
python3 -m unittest tests/test_nci_job_parser.py -v
```

## Requirements

- Python 3.6 or higher
- No external dependencies

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
