#!/usr/bin/env python3
"""gen_imgdio.py - Generate IMGDIO.BAS with bit-reversed DATA for HD61830 LSB-left ordering.
By Kayto 10/04/2026
Licensed under the MIT License. See LICENSE file for details.

Reads a data-mode HIMAGE/HIMAGE2 BAS file, bit-reverses each DATA byte
(MSB-first to LSB-first) to match the HD61830 LCD controller's pixel
ordering, and outputs a .BAS that writes bytes directly to the display
via OUT statements — no PSET/LINE, no bit unpacking.

The decoder is just:
  OUT 33,10:OUT 32,0 : OUT 33,11:OUT 32,0
  FOR Y=0 TO 63: FOR B=0 TO 29
    READ V: OUT 33,12: OUT 32,V
  NEXT B: NEXT Y

25x faster than the baseline PSET decoder (25s vs 617s).

Usage:
    python gen_imgdio.py HIMAGE.BAS IMGDIO.BAS
"""

from pathlib import Path

def rev(b):
    """Reverse bits in a byte."""
    r = 0
    for i in range(8):
        if b & (1 << i):
            r |= (1 << (7 - i))
    return r

# Read DATA from HIMAGE.BAS
src = Path("Progs/image_writer/HIMAGE.BAS")
data_vals = []
for line in src.read_text().splitlines():
    line = line.strip()
    if line and line.split()[0].isdigit():
        ln = int(line.split()[0])
        if ln >= 1000 and "DATA" in line:
            parts = line.split("DATA")[1].strip().split(",")
            data_vals.extend(int(v) for v in parts)

print(f"Total DATA values: {len(data_vals)}")
rev_vals = [rev(v) for v in data_vals]

# Build IMGDIO.BAS
out = []
out.append("1 REM IMGDIO - Direct I/O image decoder")
out.append("2 REM Writes bytes to HD61830 LCD via OUT")
out.append("3 REM DATA is bit-reversed (LSB=left)")
out.append("4 REM By kayto April 2026")
out.append("5 CUROFF:SCREEN 1")
out.append("7 OUT 33,10:OUT 32,0")
out.append("8 OUT 33,11:OUT 32,0")
out.append("10 FOR Y=0 TO 63")
out.append("20 FOR B=0 TO 29")
out.append("25 READ V")
out.append("30 OUT 33,12:OUT 32,V")
out.append("40 NEXT B")
out.append("50 NEXT Y")
out.append('70 A$=INKEY$:IF A$="" THEN 70')
out.append("80 SCREEN 0:PRINT CHR$(1);:CURON:END")

ln = 1000
per_line = 15
for i in range(0, len(rev_vals), per_line):
    chunk = rev_vals[i:i+per_line]
    out.append(f"{ln} DATA {','.join(str(v) for v in chunk)}")
    ln += 1

Path("Dev/IMGDIO.BAS").write_text("\n".join(out) + "\n")
print("Wrote Dev/IMGDIO.BAS")
print(f"First 30 original: {data_vals[:30]}")
print(f"First 30 reversed: {rev_vals[:30]}")
