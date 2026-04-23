"""
lst_to_dlst.py - Convert sjasmplus hex listing to decimal listing
By Kayto April 2026
Licensed under the MIT License. See LICENSE file for details.

Reads a .lst file produced by:
    sjasmplus --lst=PROG.lst PROG.asm

Writes a .dlst file with addresses and opcode bytes converted from hex to
decimal, making them directly comparable to Husky Hunter BASIC POKE values.

Usage:
    python lst_to_dlst.py PROG.lst              # writes PROG.dlst
    python lst_to_dlst.py PROG.lst OUT.dlst     # explicit output path
"""

import re
import sys
from pathlib import Path


def convert_line(line):
    """Convert hex address and byte columns to decimal. Leave other lines unchanged."""
    m = re.match(
        r'^(\s*\d+\s+)([0-9A-F]{4})\s{1}([0-9A-F]{2}(?:\s[0-9A-F]{2})*)([ ]{2,}.*)$',
        line.rstrip()
    )
    if not m:
        return line.rstrip()
    pre, addr, bytes_hex, rest = m.groups()
    addr_dec = str(int(addr, 16))
    dec = ' '.join(f'{int(b, 16):3d}' for b in bytes_hex.split())
    return f'{pre}{addr_dec:<6} {dec:<14}{rest}'


def convert(src: Path, dst: Path):
    lines = [convert_line(l) for l in src.read_text().splitlines()]
    dst.write_text('\n'.join(lines) + '\n')
    print(f'{src.name} -> {dst.name}  ({len(lines)} lines)')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix('.dlst')
    convert(src, dst)
