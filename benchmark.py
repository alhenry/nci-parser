#!/usr/bin/env python
"""
Simple benchmark to compare parser performance.
Creates duplicate files for testing and measures parsing speed.
"""

import os
import shutil
import time
import tempfile
from pathlib import Path

# Import the parser functions
from nci_parser.parser import parse_file_tail, parse_resource_usage_section


def create_test_files(source_file, count, test_dir):
    """Create multiple copies of a file for testing."""
    test_files = []
    for i in range(count):
        dest = os.path.join(test_dir, f"test_{i:05d}.OU")
        shutil.copy(source_file, dest)
        test_files.append(dest)
    return test_files


def benchmark_tail_reading(files):
    """Benchmark the optimized tail reading approach."""
    start = time.time()
    for f in files:
        parse_file_tail(f)
    elapsed = time.time() - start
    return elapsed


def benchmark_full_reading(files):
    """Benchmark reading full files."""
    start = time.time()
    for f in files:
        with open(f, 'r') as file:
            parse_resource_usage_section(file.read())
    elapsed = time.time() - start
    return elapsed


def main():
    # Use one of the example files
    source_file = "examples/142112589.gadi-pbs.OU"
    
    if not os.path.exists(source_file):
        print("Error: Example file not found. Run from project root.")
        return
    
    print("NCI Job Parser Performance Benchmark")
    print("=" * 50)
    print()
    
    # Test with different file counts
    test_counts = [10, 100, 500]
    
    for count in test_counts:
        with tempfile.TemporaryDirectory() as tmpdir:
            print(f"Creating {count} test files...")
            test_files = create_test_files(source_file, count, tmpdir)
            
            # Benchmark tail reading (optimized)
            tail_time = benchmark_tail_reading(test_files)
            
            # Benchmark full file reading (unoptimized)
            full_time = benchmark_full_reading(test_files)
            
            speedup = full_time / tail_time if tail_time > 0 else 0
            
            print(f"\n{count} files:")
            print(f"  Full file reading: {full_time:.3f}s ({count/full_time:.1f} files/sec)")
            print(f"  Tail reading:      {tail_time:.3f}s ({count/tail_time:.1f} files/sec)")
            print(f"  Speedup:           {speedup:.2f}x")
    
    print("\n" + "=" * 50)
    print("Note: Parallel processing provides additional speedup")
    print("      when processing many files (uses all CPU cores)")


if __name__ == "__main__":
    main()
