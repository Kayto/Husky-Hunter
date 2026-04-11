#!/usr/bin/env python3
"""gen_imgmc.py - Generate IMGMC.BAS with MC-accelerated HD61830 LCD blast.
By Kayto 11/04/2026
Licensed under the MIT License. See LICENSE file for details.

Two-phase image decoder:
  Phase 1 (BASIC): READ bit-reversed DATA into RAM buffer at 0xC000 via POKE
  Phase 2 (MC):    Z80 routine blasts 1920 bytes from buffer to HD61830

The MC routine (30 bytes at F605H) does a tight OUT loop with busy
checking — writes the entire 240x64 LCD in ~13ms.

Usage:
    python gen_imgmc.py HIMAGE.BAS IMGMC.BAS
"""

import sys
from pathlib import Path


def rev(b):
    """Reverse bits in a byte."""
    r = 0
    for i in range(8):
        if b & (1 << i):
            r |= (1 << (7 - i))
    return r


# MC routine bytes (30 bytes, installed at F605H = 62981)
# LD HL,0xC000 / LD DE,0x0780 / busy_loop: IN A,(0x21) / RLCA /
# JR C,busy_loop / LD A,0x0C / OUT (0x21),A / IN A,(0x21) / RLCA /
# JR C,busy2 / LD A,(HL) / OUT (0x20),A / INC HL / DEC DE /
# LD A,D / OR E / JR NZ,busy_loop / RET
MC_BYTES = [
    33, 0, 192,        # LD HL, 0xC000
    17, 128, 7,         # LD DE, 0x0780 (1920)
    219, 33,            # IN A, (0x21)
    7,                  # RLCA
    56, 251,            # JR C, -5
    62, 12,             # LD A, 0x0C
    211, 33,            # OUT (0x21), A
    219, 33,            # IN A, (0x21)
    7,                  # RLCA
    56, 251,            # JR C, -5
    126,                # LD A, (HL)
    211, 32,            # OUT (0x20), A
    35,                 # INC HL
    27,                 # DEC DE
    122,                # LD A, D
    179,                # OR E
    32, 233,            # JR NZ, -23
    201,                # RET
]


def main():
    if len(sys.argv) < 3:
        print("Usage: python gen_imgmc.py INPUT.BAS OUTPUT.BAS")
        sys.exit(1)

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])

    # Read DATA values from source BAS
    data_vals = []
    for line in src.read_text().splitlines():
        line = line.strip()
        if line and line.split()[0].isdigit():
            ln = int(line.split()[0])
            if ln >= 1000 and "DATA" in line:
                parts = line.split("DATA")[1].strip().split(",")
                data_vals.extend(int(v) for v in parts)

    print(f"Read {len(data_vals)} DATA values from {src}")

    # Bit-reverse each byte for HD61830 LSB-left ordering
    rev_vals = [rev(v) for v in data_vals]

    # Build IMGMC.BAS
    out = []
    out.append("1 REM IMGMC - MC LCD blast decoder")
    out.append("2 REM Phase 1: Load data to RAM buffer")
    out.append("3 REM Phase 2: MC blasts to HD61830 LCD")
    out.append("4 REM By kayto April 2026")
    out.append("5 CUROFF")
    out.append("6 FOR I=0 TO 29:READ V:POKE 62981+I,V:NEXT I")
    out.append("8 FOR I=49152 TO 51071")
    out.append("9 READ V:POKE I,V")
    out.append("10 NEXT I")
    out.append("11 SCREEN 1")
    out.append("12 OUT 33,10:OUT 32,0")
    out.append("13 OUT 33,11:OUT 32,0")
    out.append("14 P=ARG(0):X=CALL(62981)")
    out.append('70 A$=INKEY$:IF A$="" THEN 70')
    out.append("80 SCREEN 0:PRINT CHR$(1);:CURON:END")

    # MC routine DATA (line 900) + sentinel
    mc_str = ",".join(str(b) for b in MC_BYTES)
    out.append(f"900 DATA {mc_str},0")

    # Image DATA (lines 1000+)
    ln = 1000
    per_line = 15
    for i in range(0, len(rev_vals), per_line):
        chunk = rev_vals[i:i + per_line]
        out.append(f"{ln} DATA {','.join(str(v) for v in chunk)}")
        ln += 1

    dst.write_text("\n".join(out) + "\n")
    print(f"Wrote {dst} ({len(MC_BYTES)} MC bytes + {len(rev_vals)} image bytes)")


if __name__ == "__main__":
    main()
