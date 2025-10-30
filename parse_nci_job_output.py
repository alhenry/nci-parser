import re
import csv
import sys
from pathlib import Path

def parse_resource_usage_section(text):
    """
    Extracts the resource usage section from the NCI job output text.
    Returns a dictionary of key-value pairs.
    """
    # Find the resource usage section (delimited by lines of '=' and contains 'Resource Usage')
    usage_block = re.search(r"=+\n\s*Resource Usage.*?=+\n", text, re.DOTALL)
    if not usage_block:
        return None
    block = usage_block.group(0)
    result = {}
    
    for line in block.splitlines():
        # Check for the header line and extract date/time
        header_match = re.match(r"\s*Resource Usage on (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}):", line)
        if header_match:
            result['usage_date'] = header_match.group(1)
            result['usage_time'] = header_match.group(2)
            continue
        
        if ':' not in line or '===' in line:
            continue
        
        # Strategy: Find all positions where a key starts (word characters followed by colon)
        # The value extends from after the colon until the next key or end of line
        # Use a more specific pattern: keys are alphanumeric with spaces/hyphens, ending with ':'
        # Values can contain anything except start looking like a new key
        
        # Find all key positions
        key_positions = []
        for m in re.finditer(r'\b([A-Za-z][A-Za-z0-9 /-]*?):\s+', line):
            key_positions.append((m.start(), m.end(), m.group(1).strip()))
        
        # Extract key-value pairs
        for i, (start, end, key) in enumerate(key_positions):
            # Value starts after the key and colon
            value_start = end
            # Value ends at the start of next key, or end of line
            if i + 1 < len(key_positions):
                value_end = key_positions[i + 1][0]
            else:
                value_end = len(line)
            
            value = line[value_start:value_end].strip()
            if value:
                result[key] = value
    
    return result

def main(files, output_csv):
    all_rows = []
    all_keys = set()

    for file in files:
        with open(file, "r") as f:
            text = f.read()
        row = parse_resource_usage_section(text)
        if row:
            row["filename"] = Path(file).name
            all_rows.append(row)
            all_keys.update(row.keys())

    all_keys = ["filename"] + sorted(k for k in all_keys if k != "filename")
    with open(output_csv, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=all_keys, delimiter=",")
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python parse_nci_job_output.py <output.csv> <file1> [<file2> ...]")
        sys.exit(1)
    output_csv = sys.argv[1]
    files = sys.argv[2:]
    main(files, output_csv)
