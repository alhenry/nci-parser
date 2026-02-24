"""NCI Parser - Parse NCI job output files into tabular format."""

__version__ = "0.4.0"

from .parser import parse_resource_usage_section, parse_file_tail

__all__ = ["parse_resource_usage_section", "parse_file_tail"]
