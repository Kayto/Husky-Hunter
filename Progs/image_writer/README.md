# png2hba — Image to Husky Hunter BASIC Converter

Converts PNG/JPEG images to Hunter BASIC programs (`.BAS`) that display on the Husky Hunter's 240×64 monochrome LCD.

![Atkinson dither preview](preview_atkinson.png)

## Status

Working — tested on real Husky Hunter hardware. The Python converter produces valid `.BAS` source files that tokenize and render correctly on the 240×64 LCD. Note: BAS `LOAD` may corrupt line 10 (see [Generated HBA](#generated-hba)).

## Usage

```
python png2hba.py <input_image> [options]
```

### Examples

```bash
# Default: Atkinson dither, crop to fill LCD
python png2hba.py Source_Images/product-137443.png -o HUSKY.BAS

# With LCD-style preview image
python png2hba.py photo.png -o PHOTO.BAS --preview preview.png

# Threshold dither for logos/line art
python png2hba.py logo.png -o LOGO.BAS -d threshold -t 200

# Adjust brightness and contrast
python png2hba.py dark_photo.jpg -o OUTPUT.BAS -b 1.5 -c 1.3

# Invert (swap black/white)
python png2hba.py photo.png -o INVERT.BAS -i
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `-o` | `IMAGE.BAS` | Output .BAS filename |
| `-d` | `floyd-steinberg` | Dithering: `atkinson`, `floyd-steinberg`, `ordered`, `threshold` |
| `-t` | `128` | Threshold value 0–255 (threshold mode only) |
| `-f` | `fill` | Resize: `fill` (crop), `fit` (letterbox), `stretch` |
| `-b` | `1.0` | Brightness multiplier |
| `-c` | `1.0` | Contrast multiplier |
| `-i` | off | Invert image |
| `-m` | `auto` | HBA mode: `data`, `rle`, `draw`, `auto` |
| `-W` | `240` | Target width in pixels |
| `-H` | `64` | Target height in pixels |
| `--preview` | — | Save LCD-style preview PNG |

## Dithering Algorithms

| Algorithm | Best For | Notes |
|-----------|----------|-------|
| **atkinson** | Photos on LCD | High contrast, clean darks, Mac-style. Recommended. |
| **floyd-steinberg** | Smooth gradients | Classic error diffusion, smoothest tonal range |
| **ordered** | Retro aesthetic | Bayer 4×4 matrix pattern |
| **threshold** | Logos, line art | Pure black/white, smallest file, fastest render on Hunter |

## Output Modes

| Mode | Description |
|------|-------------|
| **data** | Bitmap packed as DATA bytes with bit-unpacking loop. ~8–9 KB for full LCD. Best for dense images. |
| **rle** | Run-length encoded (Y,X1,X2) triples using LINE/PSET. Compact for sparse images. |
| **draw** | Direct LINE/PSET statements. Only for very sparse images (<1000 runs). |
| **auto** | Picks rle or data based on estimated size. |

## Generated HBA

The output is a self-contained Hunter BASIC program. On the Husky Hunter:

1. Transfer to Hunter via serial or type directly
2. Enter `BAS`
3. `LOAD "HIMAGE"`
4. `RUN`

Note that some corruption was observed at line 10 (quirk?) when loading
into BAS — the file checks OK on disk but `LOAD` corrupts it. Retyping
the line fixed it. Alternatively it may be possible to send the file
via RS-232 while in BAS.
See [HUNTER_BASIC_GOTCHAS.md](../../HUNTER_BASIC_GOTCHAS.md) for details.

The program enters `SCREEN 1` (240×64 graphics mode), draws the image pixel-by-pixel, then waits for any keypress before returning to `SCREEN 0`.

### Data Mode Decoder

The bitmap is packed as bytes in DATA statements. The decoder uses successive subtraction to test bits (no bitwise AND needed — safe for Hunter BASIC):

```basic
5 CUROFF:SCREEN 1
10 FOR Y=0 TO 63
20 FOR B=0 TO 29
25 READ V:X=B*8
26 IF V=0 THEN 50
27 IF V=255 THEN LINE(X,Y)-(X+7,Y):GOTO 50
28 M=128
30 FOR P=0 TO 7
35 IF V>=M THEN PSET(X,Y):V=V-M
40 X=X+1:M=M/2:NEXT P
50 NEXT B
60 NEXT Y
```

Zero bytes and 0xFF bytes are short-circuited for speed on the 4 MHz Z80.

## Requirements

- Python 3
- Pillow (`pip install Pillow`)

## Files

| File | Description |
|------|-------------|
| `png2hba.py` | Converter script |
| `Source_Images/` | Input images |
| `HIMAGE.BAS` | Husky Hunter image program — ASCII source (tokenize before transfer) |
| `HIMAGE2.BAS` | Husky dog image program — ASCII source (tokenize before transfer) |
| `preview_atkinson.png` | LCD-style preview of HIMAGE.HBA output |
| `HUSKY_preview.png` | LCD-style preview of HIMAGE2.HBA output |

---

## Development Notes — Could It Be Faster?

The data-mode decoder is already optimised with zero-byte and 0xFF short-circuits, but drawing a full 240×64 image pixel-by-pixel through BASIC is slow!
- **Machine-code POKE loop** — Write a small Z80 routine (via `DEFUSR` / `USR()`) that unpacks each DATA byte directly into the LCD framebuffer. Would bypass the BASIC interpreter entirely for pixel writes. Potentially 10–50× faster.
- **RLE mode for sparse images** — Already implemented. For logos or line art with large blank areas, RLE uses far fewer LINE calls and finishes faster than data mode.
- **Reduce resolution** — A smaller target (e.g. 120×32) renders in roughly ¼ the time. Use `-W 120 -H 32`.
- **Pre-computed LINE runs in data mode** — Instead of bit-unpacking every byte, the converter could detect horizontal runs and emit LINE statements directly within the DATA loop. Trades file size for speed.
