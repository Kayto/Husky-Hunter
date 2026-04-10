#!/usr/bin/env python3
"""gen_hline.py - Convert DATA-mode BAS to horizontal-run (hline) format.
By Kayto 21/03/2026
Licensed under the MIT License. See LICENSE file for details.

Reads a data-mode HIMAGE/HIMAGE2 BAS file, unpacks the bitmap bytes,
computes horizontal runs per row, and outputs a .BAS with a trivial
LINE/PSET decoder.

The hline format stores per-row run counts and (X1,X2) pairs:
  DATA num_runs, x1, x2, x1, x2, ...   (per row)

The decoder is just:
  FOR Y=0 TO 63: READ N: FOR I=1 TO N: READ A,B
    IF A=B THEN PSET(A,Y) ELSE LINE(A,Y)-(B,Y)
  NEXT I: NEXT Y

No bit unpacking, no byte loops. Fastest pure-BASIC approach for
dense images since the work is done at generation time.

Usage:
    python gen_hline.py HIMAGE.BAS IMGHLIN.BAS
    python gen_hline.py HIMAGE2.BAS IMGHLN2.BAS
"""

import re
import sys


def extract_data_values(bas_path):
    """Extract all DATA values from a .BAS file."""
    values = []
    with open(bas_path, "r") as f:
        for line in f:
            # Match lines like: 1000 DATA 0,0,0,1,187,...
            m = re.match(r"\d+\s+DATA\s+(.*)", line.strip())
            if m:
                vals = m.group(1).split(",")
                values.extend(int(v.strip()) for v in vals)
    return values


def bytes_to_runs(data_values, width=240, height=64):
    """Convert flat byte array to per-row horizontal runs."""
    bpr = width // 8
    all_rows = []

    for y in range(height):
        row_bytes = data_values[y * bpr : (y + 1) * bpr]
        # Unpack bytes to pixel array
        pixels = []
        for v in row_bytes:
            for bit in range(7, -1, -1):
                pixels.append(1 if (v >> bit) & 1 else 0)

        # Find horizontal runs
        runs = []
        x = 0
        while x < width:
            if pixels[x]:
                xs = x
                while x < width and pixels[x]:
                    x += 1
                runs.append((xs, x - 1))
            else:
                x += 1
        all_rows.append(runs)

    return all_rows


def generate_hline_bas(all_rows, name="IMGHLIN", width=240, height=64):
    """Generate BAS with hline format."""
    lines = [
        f"1 REM {name} - Hline decoder",
        f"2 REM {width}x{height} LCD image",
        f"3 REM Pre-computed horizontal runs",
        f"4 REM By kayto April 2026",
        f"5 CUROFF:SCREEN 1",
        f"10 FOR Y=0 TO {height - 1}",
        f"20 READ N:IF N=0 THEN 60",
        f"30 FOR I=1 TO N",
        f"40 READ A,B",
        f"50 IF A=B THEN PSET(A,Y) ELSE LINE(A,Y)-(B,Y)",
        f"55 NEXT I",
        f"60 NEXT Y",
        f"70 A$=INKEY$:IF A$=\"\" THEN 70",
        f"80 SCREEN 0:PRINT CHR$(1);:CURON:END",
    ]

    ln = 1000
    total_runs = 0
    total_data_values = 0

    for y, runs in enumerate(all_rows):
        # Process each row: count followed by (x1,x2) pairs
        if not runs:
            lines.append(f"{ln} DATA 0")
            total_data_values += 1
            ln += 1
        else:
            # Pack run count + pairs on DATA lines
            vals = [str(len(runs))]
            for x1, x2 in runs:
                vals.append(f"{x1},{x2}")
            total_runs += len(runs)
            total_data_values += 1 + len(runs) * 2

            # Split into DATA lines (~60 chars each)
            data_str = ",".join(vals)
            while len(data_str) > 60:
                # Find a comma near position 60
                cut = data_str.rfind(",", 0, 60)
                if cut < 0:
                    cut = data_str.find(",")
                if cut < 0:
                    break
                lines.append(f"{ln} DATA {data_str[:cut]}")
                data_str = data_str[cut + 1:]
                ln += 1
            if data_str:
                lines.append(f"{ln} DATA {data_str}")
                ln += 1

    # Sentinel: Hunter BASIC FOR/NEXT executes one extra pass after
    # the counter exceeds the limit. Add DATA 0 so the extra READ N
    # on line 20 hits zero and short-circuits via IF N=0 THEN 60.
    lines.append(f"{ln} DATA 0")
    ln += 1

    return "\n".join(lines) + "\n", total_runs, total_data_values


def main():
    if len(sys.argv) < 3:
        print("Usage: python gen_hline.py INPUT.BAS OUTPUT.BAS")
        sys.exit(1)

    in_path = sys.argv[1]
    out_path = sys.argv[2]
    name = out_path.replace(".BAS", "").split("/")[-1].split("\\")[-1].upper()

    print(f"Reading:  {in_path}")
    data = extract_data_values(in_path)
    print(f"Values:   {len(data)} DATA bytes")

    rows = bytes_to_runs(data)
    print(f"Rows:     {len(rows)}")

    bas, total_runs, total_vals = generate_hline_bas(rows, name)
    print(f"Runs:     {total_runs} total horizontal segments")
    print(f"DATA:     {total_vals} values ({total_vals*3} estimated bytes)")

    with open(out_path, "w") as f:
        f.write(bas)
    print(f"Wrote:    {out_path} ({len(bas)} bytes)")


if __name__ == "__main__":
    main()
