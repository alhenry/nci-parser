import re

# Compile regex patterns once at module level for better performance
USAGE_BLOCK_PATTERN = re.compile(r"=+\n\s*Resource Usage.*?=+\n", re.DOTALL)
HEADER_PATTERN = re.compile(r"\s*Resource Usage on (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}):")
KEY_PATTERN = re.compile(r'\b([A-Za-z][A-Za-z0-9 /-]*?):\s+')


def parse_resource_usage_section(text):
    """
    Extracts the resource usage section from the NCI job output text.
    Returns a dictionary of key-value pairs.
    
    Optimized for processing large numbers of files:
    - Uses compiled regex patterns
    - Only reads the end of the file where resource usage is located
    - Minimal string operations
    """
    # Find the resource usage section (delimited by lines of '=' and contains 'Resource Usage')
    usage_block = USAGE_BLOCK_PATTERN.search(text)
    if not usage_block:
        return None
    
    block = usage_block.group(0)
    result = {}
    
    for line in block.splitlines():
        # Check for the header line and extract date/time
        header_match = HEADER_PATTERN.match(line)
        if header_match:
            result['usage_date'] = header_match.group(1)
            result['usage_time'] = header_match.group(2)
            continue
        
        if ':' not in line or '===' in line:
            continue
        
        # Find all key positions
        key_positions = []
        for m in KEY_PATTERN.finditer(line):
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


def parse_file_tail(filepath, tail_lines=30):
    """
    Read only the tail of a file where the resource usage section is likely located.
    This is much faster than reading entire large files.
    
    Args:
        filepath: Path to the file to parse
        tail_lines: Number of lines to read from the end (default 30, enough for resource section)
    
    Returns:
        Dictionary of parsed resource usage data, or None if not found
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            # Use a deque to efficiently keep only the last N lines
            from collections import deque
            lines = deque(f, maxlen=tail_lines)
            tail_text = '\n'.join(lines)
            
            # Parse the tail
            return parse_resource_usage_section(tail_text)
    except Exception:
        # Fall back to reading entire file if tail approach fails
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return parse_resource_usage_section(f.read())
        except Exception:
            return None
