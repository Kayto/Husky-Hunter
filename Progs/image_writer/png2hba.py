#!/usr/bin/env python3
"""png2hba.py - Convert PNG/JPEG images to Husky Hunter BASIC (.HBA)
By Kayto 21/03/2026
Licensed under the MIT License. See LICENSE file for details.
for display on the 240x64 monochrome LCD.

Target: Husky Hunter portable computer (1983)
        NSC800-4 @ 4MHz, DEMOS 2.2, 240x64 pixel LCD
        Hunter BASIC SCREEN 1 graphics mode

The generated .HBA program, when RUN on the Hunter, draws the image
pixel-by-pixel on the full 240x64 LCD. Press any key to exit.

Output modes:
  data  - Bitmap stored as DATA bytes, decoded with a bit-unpacking loop.
          Fixed size (~8-9 KB for full LCD). Best for dense/photographic images.
  rle   - Run-length encoded DATA (Y,X1,X2 triples), drawn with LINE/PSET.
          Variable size. Best for sparse line-art or logos.
  draw  - Direct LINE/PSET statements per run (no DATA loop).
          Only for very sparse images (<1000 runs).
  auto  - Picks rle or data based on estimated size (default).

Dithering:
  threshold       - Simple black/white cutoff
  floyd-steinberg - Classic error diffusion (best for photos)
  ordered         - Bayer matrix pattern dithering
  atkinson        - Apple Mac-style, retains more contrast

Usage:
    python png2hba.py photo.png
    python png2hba.py photo.png -o PHOTO.HBA -d atkinson
    python png2hba.py logo.png -d threshold -t 200 -i
    python png2hba.py photo.png -f fill --preview lcd.png
"""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, ImageEnhance, ImageOps
except ImportError:
    sys.exit("Pillow required: pip install Pillow")

LCD_W, LCD_H = 240, 64


# ── Image processing ─────────────────────────────────────────────────

def resize_image(img, width, height, fit):
    """Resize with aspect ratio handling."""
    if fit == "stretch":
        return img.resize((width, height), Image.LANCZOS)

    src_ratio = img.width / img.height
    dst_ratio = width / height

    if fit == "fill":
        # Crop to fill target
        if src_ratio > dst_ratio:
            new_w = int(img.height * dst_ratio)
            off = (img.width - new_w) // 2
            img = img.crop((off, 0, off + new_w, img.height))
        else:
            new_h = int(img.width / dst_ratio)
            off = (img.height - new_h) // 2
            img = img.crop((0, off, img.width, off + new_h))
        return img.resize((width, height), Image.LANCZOS)

    # fit: letterbox (pad with white)
    if src_ratio > dst_ratio:
        new_w = width
        new_h = max(1, round(width / src_ratio))
    else:
        new_h = height
        new_w = max(1, round(height * src_ratio))

    resized = img.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("L", (width, height), 255)
    canvas.paste(resized, ((width - new_w) // 2, (height - new_h) // 2))
    return canvas


def dither_threshold(img, threshold=128):
    """Simple black/white threshold."""
    return img.point(lambda x: 255 if x >= threshold else 0, "1")


def dither_floyd_steinberg(img):
    """Floyd-Steinberg error diffusion (Pillow built-in)."""
    return img.convert("1", dither=Image.FLOYDSTEINBERG)


def dither_ordered(img):
    """Bayer 4x4 ordered dithering."""
    bayer = [
        [0, 8, 2, 10], [12, 4, 14, 6],
        [3, 11, 1, 9], [15, 7, 13, 5],
    ]
    px = img.load()
    out = Image.new("1", img.size)
    op = out.load()
    for y in range(img.height):
        for x in range(img.width):
            t = (bayer[y % 4][x % 4] + 0.5) * 256 / 16
            op[x, y] = 255 if px[x, y] >= t else 0
    return out


def dither_atkinson(img):
    """Atkinson dithering (distributes 6/8 of error — retains contrast)."""
    w, h = img.size
    get_data = getattr(img, "get_flattened_data", None) or img.getdata
    px = [float(v) for v in get_data()]
    for y in range(h):
        for x in range(w):
            i = y * w + x
            old = px[i]
            new = 255.0 if old >= 128 else 0.0
            px[i] = new
            err = (old - new) / 8
            for dx, dy in [(1, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (0, 2)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    px[ny * w + nx] = max(0.0, min(255.0, px[ny * w + nx] + err))
    out = Image.new("1", (w, h))
    op = out.load()
    for y in range(h):
        for x in range(w):
            op[x, y] = 255 if px[y * w + x] >= 128 else 0
    return out


DITHERERS = {
    "threshold": dither_threshold,
    "floyd-steinberg": dither_floyd_steinberg,
    "ordered": dither_ordered,
    "atkinson": dither_atkinson,
}


# ── Bitmap encoding ──────────────────────────────────────────────────

def to_bitmap(img_1bit):
    """1-bit image -> list of rows of bools (True = dark/set pixel on LCD)."""
    px = img_1bit.load()
    return [
        [px[x, y] == 0 for x in range(img_1bit.width)]
        for y in range(img_1bit.height)
    ]


def to_bytes(bitmap):
    """Bitmap -> rows of byte values (MSB = leftmost pixel)."""
    rows = []
    for row in bitmap:
        byte_row = []
        for b in range(0, len(row), 8):
            v = 0
            for p in range(8):
                if b + p < len(row) and row[b + p]:
                    v |= 128 >> p
            byte_row.append(v)
        rows.append(byte_row)
    return rows


def to_runs(bitmap):
    """Bitmap -> list of (y, x_start, x_end) horizontal runs of set pixels."""
    runs = []
    for y, row in enumerate(bitmap):
        x = 0
        while x < len(row):
            if row[x]:
                xs = x
                while x < len(row) and row[x]:
                    x += 1
                runs.append((y, xs, x - 1))
            else:
                x += 1
    return runs


# ── HBA generation ───────────────────────────────────────────────────

def hba_data_mode(byte_rows, name, width, height):
    """HBA with DATA bytes and bit-unpacking loop.

    The loader reads each byte, tests bits from MSB to LSB using
    successive subtraction (no bitwise AND needed), and PSETs dark pixels.
    V=0 and V=255 are short-circuited for speed on the 4MHz Z80.
    """
    bpr = width // 8
    lines = [
        f"1 REM {name}",
        f"2 REM {width}x{height} LCD image",
        f"3 REM Generated by png2hba.py",
        f"4 REM By kayto 21/03/2026",
        f"5 CUROFF:SCREEN 1",
        f"10 FOR Y=0 TO {height - 1}",
        f"20 FOR B=0 TO {bpr - 1}",
        f"25 READ V:X=B*8",
        f"26 IF V=0 THEN 50",
        f"27 IF V=255 THEN LINE(X,Y)-(X+7,Y):GOTO 50",
        f"28 M=128",
        f"30 FOR P=0 TO 7",
        f"35 IF V>=M THEN PSET(X,Y):V=V-M",
        f"40 X=X+1:M=M/2:NEXT P",
        f"50 NEXT B",
        f"60 NEXT Y",
        f"70 A$=INKEY$:IF A$=\"\" THEN 70",
        f"80 SCREEN 0:PRINT CHR$(1);:CURON:END",
    ]

    all_vals = [v for row in byte_rows for v in row]
    # Append one extra row of zeros as padding — Hunter BASIC may
    # execute one additional READ after the FOR/NEXT loop exits,
    # causing a *RD Error.  The zeros are consumed harmlessly via
    # the V=0 short-circuit on line 26.
    all_vals.extend([0] * bpr)
    ln = 1000
    per_line = 15  # ~60 chars per DATA line
    for i in range(0, len(all_vals), per_line):
        chunk = all_vals[i : i + per_line]
        lines.append(f"{ln} DATA {','.join(str(v) for v in chunk)}")
        ln += 1

    return "\n".join(lines) + "\n"


def hba_rle_mode(runs, name, width, height):
    """HBA with run-length DATA (Y,X1,X2 triples) and LINE/PSET loop."""
    lines = [
        f"1 REM {name}",
        f"2 REM {width}x{height} LCD image",
        f"3 REM Generated by png2hba.py",
        f"4 REM By kayto 21/03/2026",
        f"5 CUROFF:SCREEN 1",
        f"10 READ N",
        f"20 FOR I=1 TO N",
        f"30 READ Y,A,B",
        f"40 IF A=B THEN PSET(A,Y):GOTO 60",
        f"50 LINE(A,Y)-(B,Y)",
        f"60 NEXT I",
        f"70 A$=INKEY$:IF A$=\"\" THEN 70",
        f"80 SCREEN 0:PRINT CHR$(1);:CURON:END",
    ]

    ln = 1000
    lines.append(f"{ln} DATA {len(runs)}")
    ln += 1

    per_line = 5  # 5 triples = 15 values per DATA line
    for i in range(0, len(runs), per_line):
        chunk = runs[i : i + per_line]
        vals = []
        for y, x1, x2 in chunk:
            vals.extend([str(y), str(x1), str(x2)])
        lines.append(f"{ln} DATA {','.join(vals)}")
        ln += 1

    return "\n".join(lines) + "\n"


def hba_draw_mode(runs, name, width, height):
    """HBA with direct LINE/PSET statements (no DATA loop)."""
    lines = [
        f"1 REM {name}",
        f"2 REM {width}x{height} LCD image",
        f"3 REM Generated by png2hba.py",
        f"4 REM By kayto 21/03/2026",
        f"5 CUROFF:SCREEN 1",
    ]

    ln = 10
    for y, x1, x2 in runs:
        if x1 == x2:
            lines.append(f"{ln} PSET({x1},{y})")
        else:
            lines.append(f"{ln} LINE({x1},{y})-({x2},{y})")
        ln += 1
        if ln > 64000:
            print("WARNING: Too many drawing commands, truncating", file=sys.stderr)
            break

    lines.append(f"{ln} A$=INKEY$:IF A$=\"\" THEN {ln}")
    lines.append(f"{ln + 1} SCREEN 0:PRINT CHR$(1);:CURON:END")
    return "\n".join(lines) + "\n"


# ── Preview ──────────────────────────────────────────────────────────

def generate_preview(bitmap, path, scale=4):
    """Save a scaled-up LCD-style preview image (green/dark like the real LCD)."""
    h = len(bitmap)
    w = len(bitmap[0]) if bitmap else 0
    bg = (180, 200, 160)  # LCD background
    fg = (40, 50, 35)     # LCD pixel (dark)

    img = Image.new("RGB", (w * scale, h * scale), bg)
    px = img.load()
    for y in range(h):
        for x in range(w):
            if bitmap[y][x]:
                for dy in range(scale):
                    for dx in range(scale):
                        px[x * scale + dx, y * scale + dy] = fg
    img.save(path)


# ── CLI ──────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="Convert images to Husky Hunter BASIC (.HBA) "
                    "for the 240x64 monochrome LCD.",
        epilog=(
            "examples:\n"
            "  python png2hba.py photo.png\n"
            "  python png2hba.py photo.png -o PHOTO.HBA -d atkinson\n"
            "  python png2hba.py logo.png -d threshold -t 200 -i\n"
            "  python png2hba.py photo.png -f fill --preview lcd.png\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("input", help="Input image (PNG, JPEG, BMP, GIF, etc.)")
    p.add_argument("-o", "--output",
                   help="Output .HBA file (default: IMAGE.HBA)")
    p.add_argument("-d", "--dither",
                   choices=list(DITHERERS.keys()),
                   default="floyd-steinberg",
                   help="Dithering algorithm (default: floyd-steinberg)")
    p.add_argument("-t", "--threshold", type=int, default=128,
                   help="Threshold 0-255 (threshold mode only, default: 128)")
    p.add_argument("-i", "--invert", action="store_true",
                   help="Invert image (swap black/white)")
    p.add_argument("-m", "--mode",
                   choices=["data", "rle", "draw", "auto"],
                   default="auto",
                   help="HBA output mode (default: auto)")
    p.add_argument("-f", "--fit",
                   choices=["fit", "fill", "stretch"],
                   default="fill",
                   help="Resize: fill (crop, default), fit (letterbox), stretch")
    p.add_argument("-b", "--brightness", type=float, default=1.0,
                   help="Brightness multiplier (default: 1.0)")
    p.add_argument("-c", "--contrast", type=float, default=1.0,
                   help="Contrast multiplier (default: 1.0)")
    p.add_argument("--preview", metavar="FILE",
                   help="Save LCD-style preview image (PNG)")
    p.add_argument("-W", "--width", type=int, default=LCD_W,
                   help=f"Target width in pixels (default: {LCD_W})")
    p.add_argument("-H", "--height", type=int, default=LCD_H,
                   help=f"Target height in pixels (default: {LCD_H})")
    args = p.parse_args()

    # ── Load image ──
    src = Path(args.input)
    if not src.exists():
        sys.exit(f"Error: {src} not found")

    img = Image.open(src)
    print(f"Input:    {src.name} ({img.width}x{img.height}, {img.mode})")

    # Handle transparency by compositing against white
    if img.mode in ("RGBA", "LA", "PA"):
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    img = img.convert("L")

    # ── Resize ──
    img = resize_image(img, args.width, args.height, args.fit)
    print(f"Resize:   {img.width}x{img.height} ({args.fit})")

    # ── Adjustments ──
    if args.brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(args.brightness)
    if args.contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(args.contrast)
    if args.invert:
        img = ImageOps.invert(img)

    # ── Dither ──
    if args.dither == "threshold":
        img_1bit = dither_threshold(img, args.threshold)
    else:
        img_1bit = DITHERERS[args.dither](img)
    print(f"Dither:   {args.dither}")

    # ── Encode ──
    bitmap = to_bitmap(img_1bit)
    byte_rows = to_bytes(bitmap)
    runs = to_runs(bitmap)

    total = args.width * args.height
    filled = sum(sum(r) for r in bitmap)
    pct = filled * 100 // total if total else 0
    print(f"Pixels:   {filled}/{total} set ({pct}% fill)")
    print(f"Runs:     {len(runs)} horizontal segments")

    # ── Mode selection ──
    mode = args.mode
    if mode == "auto":
        # Estimate output sizes (chars)
        data_est = sum(len(str(v)) + 1 for row in byte_rows for v in row) + 300
        rle_est = len(runs) * 12 + 300
        mode = "rle" if (len(runs) < 2000 and rle_est < data_est) else "data"

    # ── Generate HBA ──
    name = Path(args.output).stem.upper() if args.output else "IMAGE"
    if mode == "data":
        hba = hba_data_mode(byte_rows, name, args.width, args.height)
    elif mode == "rle":
        hba = hba_rle_mode(runs, name, args.width, args.height)
    else:
        hba = hba_draw_mode(runs, name, args.width, args.height)

    hba_lines = hba.strip().split("\n")
    print(f"Mode:     {mode} ({len(hba_lines)} lines, {len(hba)} bytes)")

    if len(hba) > 40000:
        print("WARNING:  Large output - may exceed Hunter BASIC memory")

    # ── Write ──
    out = Path(args.output) if args.output else Path("IMAGE.HBA")
    out.write_text(hba)
    print(f"Wrote:    {out}")

    # ── Preview ──
    if args.preview:
        generate_preview(bitmap, args.preview)
        print(f"Preview:  {args.preview}")


if __name__ == "__main__":
    main()
