"""
Parser for NCI account/quota output files (from ``nci_account`` or similar).

Produces three tables:
- usage-global   : Overall usage summary + stakeholder breakdown
- usage-users    : Per-user usage and reserved amounts
- storage-global : Per-filesystem storage usage + stakeholder breakdown
"""

import re


# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

_USAGE_HEADER   = re.compile(r'Usage Report:\s*Project=(\S+)\s+Period=(\S+)')
_STORAGE_HEADER = re.compile(r'Storage Usage Report:\s*Project=(\S+)')

# Overall totals (key:   value unit)
_TOTAL_LINE = re.compile(r'^\s*(Grant|Used|Reserved|Avail):\s+([\d.,]+\s+\S+)\s*$',
                         re.MULTILINE)

# Stakeholder (usage) row — name  grant  used  avail
# Use [^\S\n] (non-newline whitespace) so the name doesn't span lines
_SH_USAGE_ROW = re.compile(
    r'^(?![-=\s])(\S[^\n]*?)\s{2,}'
    r'([\d.,]+\s+\S+)\s+'
    r'([\d.,]+\s+\S+)\s+'
    r'([\d.,]+\s+\S+)\s*$',
    re.MULTILINE,
)

# User row — username  used  reserved
_USER_ROW = re.compile(
    r'^(\S+)\s{2,}'
    r'([\d.,]+\s+\S+)\s+'
    r'([\d.,]+\s+\S+)\s*$',
    re.MULTILINE,
)

# Filesystem row — fsname  used  iused  [allocation  iallocation]
# fsname must start with a letter/digit.
# Requires at least 3 number-unit tokens (used + iused + optional allocation pair).
# This distinguishes filesystem lines (3-5 tokens) from stakeholder lines (2 tokens).
_FS_ROW = re.compile(
    r'^([A-Za-z0-9]\S*)\s{2,}'
    r'([\d.,]+\s+\S+)\s+'
    r'([\d.,]+\s+\S+)'
    r'(?:\s+([\d.,]+\s+\S+)\s+'
    r'([\d.,]+\s+\S+))?'
    r'\s*$',
    re.MULTILINE,
)

# iused must NOT itself look like a "number unit" followed by more numbers on the same line
# → Actually we distinguish by requiring iused to be followed by end-of-line OR allocation pair,
#   never a lone third token. The regex above already does this correctly for 3-token lines.
# A number+unit token
_NUM_UNIT = re.compile(r'^[\d.,]+\s+\S+$')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _totals(block):
    return {m.group(1): m.group(2).strip() for m in _TOTAL_LINE.finditer(block)}


def _split_usage_storage(text):
    sm = _STORAGE_HEADER.search(text)
    if sm:
        return text[:sm.start()], text[sm.start():]
    return text, ''


# ---------------------------------------------------------------------------
# Public parse functions
# ---------------------------------------------------------------------------

def parse_usage_global(text):
    """
    Parse the overall usage summary + stakeholder rows.

    Columns: project, period, grant, used, reserved, avail,
             stakeholder, stakeholder_grant, stakeholder_used, stakeholder_avail
    """
    usage_block, _ = _split_usage_storage(text)

    hm = _USAGE_HEADER.search(usage_block)
    if not hm:
        return []
    project, period = hm.group(1), hm.group(2)

    t = _totals(usage_block)
    base = dict(project=project, period=period,
                grant=t.get('Grant', ''), used=t.get('Used', ''),
                reserved=t.get('Reserved', ''), avail=t.get('Avail', ''))

    sh_rows = []
    for m in _SH_USAGE_ROW.finditer(usage_block):
        name = m.group(1).strip()
        if name.lower() == 'stakeholder':
            continue
        sh_rows.append({**base,
                        'stakeholder':       name,
                        'stakeholder_grant': m.group(2).strip(),
                        'stakeholder_used':  m.group(3).strip(),
                        'stakeholder_avail': m.group(4).strip()})

    if sh_rows:
        return sh_rows
    return [{**base, 'stakeholder': '', 'stakeholder_grant': '',
             'stakeholder_used': '', 'stakeholder_avail': ''}]


def parse_usage_users(text):
    """
    Parse the per-user usage table.

    Columns: project, period, username, used, reserved
    """
    usage_block, _ = _split_usage_storage(text)

    hm = _USAGE_HEADER.search(usage_block)
    if not hm:
        return []
    project, period = hm.group(1), hm.group(2)

    rows = []
    for m in _USER_ROW.finditer(usage_block):
        username = m.group(1).strip()
        if username.lower() == 'user':
            continue
        rows.append(dict(project=project, period=period,
                         username=username,
                         used=m.group(2).strip(),
                         reserved=m.group(3).strip()))
    return rows


def _parse_storage_stakeholders(sub_block):
    """
    Extract stakeholder rows from the text between two filesystem lines.

    Each stakeholder line is either:
      "Name   alloc  ialloc"   (named)
      "       alloc  ialloc"   (unnamed / blank name)
    We split on 2+ spaces and expect exactly 2 or 3 tokens where the last
    two look like  "<number> <unit>".
    """
    results = []
    for line in sub_block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('-') or stripped.startswith('='):
            continue
        # Split on runs of 2+ spaces
        parts = [p.strip() for p in re.split(r'\s{2,}', stripped) if p.strip()]
        # We need the last two parts to be "number unit" tokens
        if len(parts) < 2:
            continue
        # Try to identify how many trailing tokens are "number unit"
        # Walk from the right: collect tokens that match "digits unit"
        num_tokens = []
        name_parts = []
        for part in reversed(parts):
            if re.match(r'^[\d.,]+\s+\S+$', part):
                num_tokens.insert(0, part)
            else:
                # Once we hit a non-number, everything to the left is the name
                break
        name_parts = parts[:len(parts) - len(num_tokens)]

        if len(num_tokens) < 2:
            continue

        # Skip header lines
        name = ' '.join(name_parts).strip()
        if name.lower() in ('stakeholder', 'filesystem', 'allocation', ''):
            name = ''
        # Last two num_tokens are allocation, iallocation
        alloc  = num_tokens[-2]
        ialloc = num_tokens[-1]
        results.append((name, alloc, ialloc))
    return results


def parse_storage_global(text):
    """
    Parse the storage usage report.

    Uses a state machine over lines:
      - A line with a word name + 3+ number-unit tokens  → new filesystem
      - "Stakeholder ..." header line                    → switch to stakeholder mode
      - A data line in stakeholder mode                  → stakeholder row
      - Blank / separator lines                          → skip

    Columns: project, filesystem, used, iused, allocation, iallocation,
             stakeholder, stakeholder_allocation, stakeholder_iallocation
    """
    _, storage_block = _split_usage_storage(text)

    sm = _STORAGE_HEADER.search(storage_block)
    if not sm:
        return []
    project = sm.group(1)

    num_unit = re.compile(r'^[\d.,]+\s+\S+$')

    def split_tokens(line):
        return [p.strip() for p in re.split(r'\s{2,}', line.strip()) if p.strip()]

    def is_num(tok):
        return bool(num_unit.match(tok))

    rows = []
    current_fs = None
    in_stakeholder = False
    seen_sh_separator = False  # True once we've passed the opening '---' of a sh block

    for raw_line in storage_block.splitlines():
        line = raw_line.strip()

        # Skip blanks and the section/column headers
        if not line or line.startswith('='):
            continue
        # Separator lines (---):
        #   - First separator after "Stakeholder" header → opening divider (skip, stay in mode)
        #   - Second separator → closing divider (exit stakeholder mode)
        if line.startswith('-'):
            if in_stakeholder:
                if not seen_sh_separator:
                    seen_sh_separator = True   # opening divider — stay in mode
                else:
                    in_stakeholder = False     # closing divider — exit mode
                    seen_sh_separator = False
            continue
        if _STORAGE_HEADER.match(line):
            continue
        if re.match(r'^Filesystem\b', line, re.IGNORECASE):
            continue

        # "Stakeholder  Allocation  iAllocation" header → enter stakeholder mode
        if re.match(r'^Stakeholder\b', line, re.IGNORECASE):
            in_stakeholder = True
            seen_sh_separator = False
            continue

        parts = split_tokens(line)
        if not parts:
            continue

        num_parts = [p for p in parts if is_num(p)]
        str_parts = [p for p in parts if not is_num(p)]

        # A filesystem line has 1 name + at least 2 numeric tokens.
        # Never treat a line as a filesystem while inside a stakeholder block.
        is_fs_line = (not in_stakeholder
                      and len(str_parts) == 1
                      and len(num_parts) >= 2)

        if in_stakeholder and not is_fs_line:
            # Stakeholder data: 0 or 1 name token + 2 num tokens
            if len(num_parts) >= 2 and current_fs is not None:
                name   = str_parts[0] if str_parts else ''
                alloc  = num_parts[-2]
                ialloc = num_parts[-1]
                rows.append({**current_fs,
                             'stakeholder':             name,
                             'stakeholder_allocation':  alloc,
                             'stakeholder_iallocation': ialloc})
        else:
            # Filesystem line
            if is_fs_line:
                in_stakeholder = False
                fs_name   = str_parts[0]
                fs_used   = num_parts[0]
                fs_iused  = num_parts[1]
                fs_alloc  = num_parts[2] if len(num_parts) > 2 else ''
                fs_ialloc = num_parts[3] if len(num_parts) > 3 else ''
                current_fs = dict(project=project, filesystem=fs_name,
                                  used=fs_used, iused=fs_iused,
                                  allocation=fs_alloc, iallocation=fs_ialloc)
                rows.append({**current_fs,
                             'stakeholder': '',
                             'stakeholder_allocation': '',
                             'stakeholder_iallocation': ''})

    # Remove placeholder base-rows that are followed by stakeholder rows
    # for the same filesystem (identified by having non-empty stakeholder_allocation)
    clean = []
    i = 0
    while i < len(rows):
        row = rows[i]
        if (row['stakeholder'] == ''
                and row['stakeholder_allocation'] == ''
                and i + 1 < len(rows)
                and rows[i + 1]['filesystem'] == row['filesystem']
                and rows[i + 1]['stakeholder_allocation'] != ''):
            i += 1  # skip placeholder
            continue
        clean.append(row)
        i += 1

    return clean


# ---------------------------------------------------------------------------
# Convenience wrapper
# ---------------------------------------------------------------------------

VALID_OUTPUTS = ('usage-global', 'usage-users', 'storage-global')


def parse_quota_file(filepath):
    """Parse a quota file. Returns dict with all three tables."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as fh:
        text = fh.read()
    return {
        'usage-global':   parse_usage_global(text),
        'usage-users':    parse_usage_users(text),
        'storage-global': parse_storage_global(text),
    }
