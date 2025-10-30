#!/usr/bin/env python3
"""
NCI Job Parser
A simple parser to parse job submission output from Australia's National Computing Infrastructure (NCI)
and write the information into a tabular file format.
"""

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional


class NCIJobParser:
    """Parser for NCI job submission output."""
    
    # Define output field names as class constant
    FIELDNAMES = ['line_number', 'job_id', 'job_id_full', 'server', 'status']
    
    def __init__(self):
        """Initialize the parser with regex patterns for NCI job output."""
        # Pattern to match typical PBS/Torque job submission output
        # Example: "12345678.gadi-pbs" or just "12345678"
        self.job_id_pattern = re.compile(r'^(\d+)(?:\.[\w-]+)?$')
        
        # Pattern to match full job submission line with status
        # Example: "Job 12345678.gadi-pbs submitted" or "Job 12345678.gadi-pbs queued"
        self.job_submission_pattern = re.compile(
            r'(?:Job\s+)?(\d+(?:\.[\w-]+)?)\s+(submitted|queued)',
            re.IGNORECASE
        )
    
    def parse_job_line(self, line: str) -> Optional[Dict[str, str]]:
        """
        Parse a single line of NCI job submission output.
        
        Args:
            line: A line from the job submission output
            
        Returns:
            Dictionary containing job information, or None if parsing fails
        """
        line = line.strip()
        if not line:
            return None
        
        # Try to match job submission pattern first
        match = self.job_submission_pattern.search(line)
        if match:
            job_id_full = match.group(1)
            status = match.group(2).lower()
            job_id, server = self._split_job_id(job_id_full)
            return {
                'job_id': job_id,
                'job_id_full': job_id_full,
                'server': server or '',
                'status': status
            }
        
        # Try to match just a job ID
        match = self.job_id_pattern.match(line)
        if match:
            job_id_full = match.group(0)
            job_id, server = self._split_job_id(job_id_full)
            return {
                'job_id': job_id,
                'job_id_full': job_id_full,
                'server': server or '',
                'status': 'submitted'
            }
        
        return None
    
    def _split_job_id(self, job_id_full: str) -> tuple:
        """
        Split a full job ID into job number and server name.
        
        Args:
            job_id_full: Full job ID (e.g., "12345678.gadi-pbs")
            
        Returns:
            Tuple of (job_id, server_name)
        """
        if '.' in job_id_full:
            parts = job_id_full.split('.', 1)
            return parts[0], parts[1]
        return job_id_full, None
    
    def parse_file(self, input_file: Path) -> List[Dict[str, str]]:
        """
        Parse a file containing NCI job submission output.
        
        Args:
            input_file: Path to the input file
            
        Returns:
            List of dictionaries containing parsed job information
        """
        jobs = []
        
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    job_info = self.parse_job_line(line)
                    if job_info:
                        job_info['line_number'] = str(line_num)
                        jobs.append(job_info)
        except FileNotFoundError:
            print(f"Error: File '{input_file}' not found.", file=sys.stderr)
            sys.exit(1)
        except IOError as e:
            print(f"Error reading file '{input_file}': {e}", file=sys.stderr)
            sys.exit(1)
        
        return jobs
    
    def parse_text(self, text: str) -> List[Dict[str, str]]:
        """
        Parse text containing NCI job submission output.
        
        Args:
            text: Text containing job submission output
            
        Returns:
            List of dictionaries containing parsed job information
        """
        jobs = []
        
        for line_num, line in enumerate(text.splitlines(), 1):
            job_info = self.parse_job_line(line)
            if job_info:
                job_info['line_number'] = str(line_num)
                jobs.append(job_info)
        
        return jobs
    
    def write_csv(self, jobs: List[Dict[str, str]], output_file: Path) -> None:
        """
        Write parsed job information to a CSV file.
        
        Args:
            jobs: List of job dictionaries
            output_file: Path to the output CSV file
        """
        if not jobs:
            print("Warning: No jobs to write.", file=sys.stderr)
            return
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()
                writer.writerows(jobs)
            
            print(f"Successfully wrote {len(jobs)} job(s) to '{output_file}'")
        except IOError as e:
            print(f"Error writing to file '{output_file}': {e}", file=sys.stderr)
            sys.exit(1)
    
    def write_tsv(self, jobs: List[Dict[str, str]], output_file: Path) -> None:
        """
        Write parsed job information to a TSV (tab-separated values) file.
        
        Args:
            jobs: List of job dictionaries
            output_file: Path to the output TSV file
        """
        if not jobs:
            print("Warning: No jobs to write.", file=sys.stderr)
            return
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES, delimiter='\t')
                writer.writeheader()
                writer.writerows(jobs)
            
            print(f"Successfully wrote {len(jobs)} job(s) to '{output_file}'")
        except IOError as e:
            print(f"Error writing to file '{output_file}': {e}", file=sys.stderr)
            sys.exit(1)


def main():
    """Main entry point for the NCI job parser."""
    parser = argparse.ArgumentParser(
        description='Parse NCI job submission output and write to tabular format'
    )
    parser.add_argument(
        'input_file',
        type=Path,
        help='Input file containing NCI job submission output'
    )
    parser.add_argument(
        'output_file',
        type=Path,
        help='Output file for parsed job information'
    )
    parser.add_argument(
        '-f', '--format',
        choices=['csv', 'tsv'],
        default='csv',
        help='Output file format (default: csv)'
    )
    
    args = parser.parse_args()
    
    # Create parser and parse input
    job_parser = NCIJobParser()
    jobs = job_parser.parse_file(args.input_file)
    
    if not jobs:
        print("Warning: No jobs found in input file.", file=sys.stderr)
        return
    
    # Write output in specified format
    if args.format == 'csv':
        job_parser.write_csv(jobs, args.output_file)
    else:
        job_parser.write_tsv(jobs, args.output_file)


if __name__ == '__main__':
    main()
