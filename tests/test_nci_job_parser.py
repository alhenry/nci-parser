#!/usr/bin/env python3
"""
Unit tests for NCI Job Parser
"""

import unittest
import tempfile
from pathlib import Path
import csv
import sys
import os

# Add parent directory to path to import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nci_job_parser import NCIJobParser


class TestNCIJobParser(unittest.TestCase):
    """Test cases for NCIJobParser class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = NCIJobParser()
    
    def test_parse_job_id_with_server(self):
        """Test parsing a job ID with server name."""
        result = self.parser.parse_job_line("12345678.gadi-pbs")
        self.assertIsNotNone(result)
        self.assertEqual(result['job_id'], '12345678')
        self.assertEqual(result['job_id_full'], '12345678.gadi-pbs')
        self.assertEqual(result['server'], 'gadi-pbs')
        self.assertEqual(result['status'], 'submitted')
    
    def test_parse_job_id_without_server(self):
        """Test parsing a job ID without server name."""
        result = self.parser.parse_job_line("12345678")
        self.assertIsNotNone(result)
        self.assertEqual(result['job_id'], '12345678')
        self.assertEqual(result['job_id_full'], '12345678')
        self.assertEqual(result['server'], '')
        self.assertEqual(result['status'], 'submitted')
    
    def test_parse_job_submission_message(self):
        """Test parsing a job submission message."""
        result = self.parser.parse_job_line("Job 12345678.gadi-pbs submitted")
        self.assertIsNotNone(result)
        self.assertEqual(result['job_id'], '12345678')
        self.assertEqual(result['job_id_full'], '12345678.gadi-pbs')
        self.assertEqual(result['server'], 'gadi-pbs')
        self.assertEqual(result['status'], 'submitted')
    
    def test_parse_job_queued_message(self):
        """Test parsing a job queued message."""
        result = self.parser.parse_job_line("Job 87654321.gadi-pbs queued")
        self.assertIsNotNone(result)
        self.assertEqual(result['job_id'], '87654321')
        self.assertEqual(result['job_id_full'], '87654321.gadi-pbs')
        self.assertEqual(result['server'], 'gadi-pbs')
        self.assertEqual(result['status'], 'queued')
    
    def test_parse_empty_line(self):
        """Test parsing an empty line."""
        result = self.parser.parse_job_line("")
        self.assertIsNone(result)
    
    def test_parse_whitespace_line(self):
        """Test parsing a line with only whitespace."""
        result = self.parser.parse_job_line("   ")
        self.assertIsNone(result)
    
    def test_parse_invalid_line(self):
        """Test parsing an invalid line."""
        result = self.parser.parse_job_line("This is not a job ID")
        self.assertIsNone(result)
    
    def test_parse_text(self):
        """Test parsing text with multiple job lines."""
        text = """12345678.gadi-pbs
Job 87654321.gadi-pbs submitted
11111111"""
        jobs = self.parser.parse_text(text)
        self.assertEqual(len(jobs), 3)
        self.assertEqual(jobs[0]['job_id'], '12345678')
        self.assertEqual(jobs[1]['job_id'], '87654321')
        self.assertEqual(jobs[2]['job_id'], '11111111')
    
    def test_parse_file(self):
        """Test parsing a file with job output."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("12345678.gadi-pbs\n")
            f.write("Job 87654321.gadi-pbs submitted\n")
            f.write("\n")
            f.write("11111111\n")
            temp_file = f.name
        
        try:
            jobs = self.parser.parse_file(Path(temp_file))
            self.assertEqual(len(jobs), 3)
            self.assertEqual(jobs[0]['job_id'], '12345678')
            self.assertEqual(jobs[1]['job_id'], '87654321')
            self.assertEqual(jobs[2]['job_id'], '11111111')
        finally:
            os.unlink(temp_file)
    
    def test_write_csv(self):
        """Test writing jobs to CSV file."""
        jobs = [
            {'line_number': '1', 'job_id': '12345678', 'job_id_full': '12345678.gadi-pbs', 
             'server': 'gadi-pbs', 'status': 'submitted'},
            {'line_number': '2', 'job_id': '87654321', 'job_id_full': '87654321.gadi-pbs', 
             'server': 'gadi-pbs', 'status': 'submitted'}
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            temp_file = f.name
        
        try:
            self.parser.write_csv(jobs, Path(temp_file))
            
            # Verify the CSV file
            with open(temp_file, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[0]['job_id'], '12345678')
                self.assertEqual(rows[1]['job_id'], '87654321')
        finally:
            os.unlink(temp_file)
    
    def test_write_tsv(self):
        """Test writing jobs to TSV file."""
        jobs = [
            {'line_number': '1', 'job_id': '12345678', 'job_id_full': '12345678.gadi-pbs', 
             'server': 'gadi-pbs', 'status': 'submitted'}
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.tsv') as f:
            temp_file = f.name
        
        try:
            self.parser.write_tsv(jobs, Path(temp_file))
            
            # Verify the TSV file
            with open(temp_file, 'r') as f:
                reader = csv.DictReader(f, delimiter='\t')
                rows = list(reader)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]['job_id'], '12345678')
        finally:
            os.unlink(temp_file)
    
    def test_split_job_id_with_server(self):
        """Test splitting job ID with server."""
        job_id, server = self.parser._split_job_id("12345678.gadi-pbs")
        self.assertEqual(job_id, "12345678")
        self.assertEqual(server, "gadi-pbs")
    
    def test_split_job_id_without_server(self):
        """Test splitting job ID without server."""
        job_id, server = self.parser._split_job_id("12345678")
        self.assertEqual(job_id, "12345678")
        self.assertIsNone(server)


if __name__ == '__main__':
    unittest.main()
