# Terrain - Point-to-Point Radio Link Profiler

Inspired by a real world use of the Husky Hunter and dedicated to Yeoman of Signals Palmer.


Micro Live S02E02
https://www.youtube.com/watch?v=y1ZBr3NInow&t=739s

## Overview

A conceptual recreation of a Hunter BASIC program for radio link planning on the Husky Hunter's 240x64 pixel LCD. Given a pre-loaded contour dataset for an operational area, the user enters start and end grid coordinates, mast heights, frequency and polarisation. The program automatically extracts a terrain profile by computing bearing-line / contour-segment intersections, plots the full-screen profile with LOS overlay, and calculates total path loss in dB.

No external maps needed in the field — the Hunter is a self-contained terrain analysis tool.

## Status

**V1.0 — Working on real Husky Hunter hardware.** Terrain profile plotting, LOS overlay, and dB path loss display confirmed. The included `CONTOUR.DAT` is a development/limited-area file (single 10×10 km tile). Area coverage and dataset size are in development.

| Feature | Status |
| ------- | ------ |
| Menu, Load Area, Link Analysis form | Confirmed on hardware |
| File I/O (CONTOUR.DAT, all 22 segments) | errors to investigate? |
| Contour extraction / intersection solver | Confirmed on hardware |
| Terrain profile plot (240×64 SCREEN 1) | Confirmed on hardware |
| LOS line overlay (dashed) + antenna masts | Confirmed on hardware |
| dB path loss display | Confirmed on hardware |
| asc2contour.py → Hunter compatibility | Confirmed |
| ON ERROR EOF handler (CP/M record padding) | Confirmed on hardware |
| Larger operational area datasets | In development |
| Performance with large contour files (~92 KB) | In development |
| Binary contour format (BDOS reader) | In development |
| Fresnel zone / Deygout multi-obstruction | Future |

## Background

Military signal units used programs like these to:

* Assess viability of radio links between two points
* Plot the ground profile along a bearing between stations
* Identify terrain obstructions blocking line-of-sight
* Estimate diffraction and terrain-related path losses
* Choose optimal antenna heights and relay positions

### Operational Workflow

```
PRE-DEPLOYMENT (HQ/Sigs):         IN THE FIELD:

OS Terrain 50 data (.asc)          1. Load Area
        ↓                          2. Link Analysis
asc2contour.py                        Enter start/end coords
  (marching squares +                 Mast heights, freq, polar
   Douglas-Peucker)                         ↓
        ↓                          Auto-extract profile from
CONTOUR.DAT                        contour crossings along bearing
        ↓                                  ↓
Upload to Hunter                   Full-screen profile plot
via RS-232 at 4800 baud            + LOS + dB overlay
        ↓                                  ↓
Store on RAM-disk                  GO / NO-GO decision
(covers operational area)
```

Original 1980s workflow probably used hand-digitised contours from 1:50,000 paper maps. The `asc2contour.py` script automates this using free OS Terrain 50 elevation data.

### Husky Hunter (1983)

Ruggedised portable field computer by DVW Microelectronics / Husky Computers Ltd, Coventry.

| Spec | Detail |
| ---- | ------ |
| CPU | NSC800-4 @ 4 MHz (CMOS Z80-compatible) |
| RAM | 80K / 144K / 208K, battery-backed CMOS |
| ROM | 48K firmware in EPROMs, paged through 16K window |
| Display | 240 x 64 dot LCD (8x40 visible, 24x80 virtual) |
| Graphics | Full 240x64 pixel addressing, 5 char sizes (BASIC only) |
| Serial | RS-232 up to 4800 baud |
| OS | DEMOS 2.2 (CP/M 2.2 derivative, RAM-disk) |

* MAME source: https://github.com/mamedev/mame/blob/master/src/mame/husky/husky.cpp

## Screens

### Opening Menu

```
  TERRAIN PROFILER V1.0

Area: CONTOUR.DAT  Loaded

1. Load Area
2. Link Analysis
3. Exit

?
```

### Link Analysis Form

```
Start Coords:         ? 4010,3150
End Coords:           ? 4220,3150
Mast Height - TX:     ? 10
Mast Height - RX:     ? 10
Polar'n 0=Hz 1=Vt:   ? 1
Freq (30-5000MHz):    ? 150

PROFILE WILL TAKE 8s - PLEASE WAIT.
```

After the last input, the program:

1. Extracts the terrain profile from contour data
2. Estimates processing time
3. Plots the full-screen profile with LOS and dB overlay

### Profile Plot

Full 240x64 visible LCD — no axes or labels, just terrain and LOS:

![Terrain profile on Husky Hunter](../images/20260320_234803.jpg)

* **Terrain**: Bresenham line segments between contour crossings, spanning 0-239 x 0-63
* **LOS**: Dashed line (every other pixel) from TX to RX antenna top
* **Antenna masts**: Vertical pixel lines at x=0 (TX) and x=239 (RX)
* **dB overlay**: Total path loss (FSPL + diffraction) displayed mid-screen
* Any key returns to menu

## Contour Data Format

The area file holds digitised contour polylines from 1:50,000 maps. First line defines the area, then contour segments follow:

```
"A",4000,3000,300,300
"C",200,3
55,100
2,5
3,4
"C",220,2
65,100
0,100
"C",250,2
78,120
0,60
...
```

| Line | Meaning |
| ---- | ------- |
| `"A",4000,3000,300,300` | Area: origin easting 4000, northing 3000 (hectometres), width 300, height 300 hm |
| `"C",200,3` | Contour at 200m ASL, 3 vertices follow |
| `55,100` | First vertex: absolute easting 55, northing 100 (offset from origin, in hectometres) |
| `2,5` | Second vertex: delta from previous (+2 east, +5 north) = absolute 57,105 |
| `3,4` | Third vertex: delta from previous (+3 east, +4 north) = absolute 60,109 |

* **Quoted string markers**: `"A"` and `"C"` must be double-quoted in the file — Hunter BASIC's `INPUT#` reads unquoted values as numeric, causing a type mismatch on string variables
* **Delta encoding**: first vertex of each segment is absolute, subsequent vertices are deltas from the previous vertex. Reduces file size ~27% vs absolute coordinates.
* Coordinates in **hectometres** (100m units) — matches 1:50,000 map grid resolution
* Multiple segments at the same level are separate `C` lines (for islands, re-entrant valleys)
* Typical vertex spacing ~100-200m along each contour

### Storage Budget (208K Hunter)

| Item | Size |
| ---- | ---- |
| Total RAM | 208K |
| CPU address space (CP/M + TPA) | 64K |
| RAM-disk (bank-switched) | 144K |
| File system overhead | ~6K |
| **STAT reports available** | **~138K** |
| TERRAIN.HBA program | ~9K |
| **Available for contour data** | **~129K** |

Benchmarked with real OS Terrain 50 data, delta-encoded, `-s 200 -m 10`:

| Interval | Coverage | Tiles | File Size | Fits 129K? |
| -------- | -------- | ----- | --------- | ---------- |
| **10m** | **50x50 km** | **25** | **92 KB** | **Yes** |
| 10m | 60x60 km | 36 | 141 KB | No |
| 10m | 40x40 km | 16 | 66 KB | Yes |

The file is read sequentially from disk — not loaded into BASIC memory. Only the D(100)/H(100) profile arrays reside in RAM.

## Profile Extraction

When the user enters start and end coordinates, the program reads every contour segment from the area file and solves 2D line-segment intersections along the bearing line. Each crossing is recorded as (chainage, contour height). Ground heights at TX/RX are estimated from the nearest crossings, and all points are insertion-sorted by chainage into the D(), H() profile arrays.

## Path Loss Calculation

Computed automatically after profile extraction and overlaid on the plot:

* **FSPL** (free-space path loss) from distance and frequency
* **LOS clearance** via segment-crossing analysis along the full profile
* **Knife-edge diffraction** (ITU single-obstruction model) when terrain blocks LOS
* **Total** displayed as integer dB on the profile screen

## Program Structure (TERRAIN.HBA)

| Lines | Section |
| ----- | ------- |
| 100-144 | Init: DIM, defaults, area variables, power-off inhibit |
| 200-315 | Opening menu: Load Area / Link Analysis / Exit |
| 500-560 | Load area file (reads header only) |
| 600-674 | Link analysis form: coords, mast heights, polar, freq → extract → plot |
| 800-990 | Plot profile: auto-scale, SCREEN 1, Bresenham terrain, LOS, dB overlay |
| 1120-1245 | LOS line (dashed) with antenna masts |
| 1900-1920 | Exit: clear power-off inhibit, END |
| 9000-9065 | Bresenham line-drawing subroutine |
| 9100-9205 | Calculate FSPL + diffraction, overlay dB on profile |
| 9300-9460 | Extract profile from contours (intersection solver + sort) |
| 9500-9515 | Wait for ENTER keypress |

## Key Variables

| Var | Purpose |
| --- | ------- |
| D(), H() | Chainage (km) and height (m ASL) arrays, max 100 |
| NP | Number of profile points |
| TH, RH | TX and RX mast heights (m) |
| FR | Frequency (MHz), range 30-5000 |
| PL | Polarisation: 0=Hz, 1=Vt |
| AF$ | Area filename (default CONTOUR.DAT) |
| AL | Area loaded flag (0/1) |
| AE, AN | Area origin easting/northing (hectometres) |
| AW, AH | Area width/height (hectometres) |
| BE, BN | TX offset from origin (hectometres) |
| RE, RN | RX offset from origin (hectometres) |
| BD | Bearing distance (hectometres) |
| TG, RG | TX/RX ground height (m, from nearest contour) |
| TL | Total path loss (dB) |

## Hardware Addresses

```
POKE 63416,1   (F7B8 NYMPHO)  — inhibit power-off key
POKE 63419,1   (F7BB FOREVER) — prevent auto switch-off
```

Set to 1 at startup (line 140), cleared to 0 on exit (line 1905).

## Build

No build required. `TERRAIN.HBA` is a Hunter BASIC source file:

1. Transfer to Hunter via serial (`INP` at 4800 baud) or type directly
2. `LOAD "TERRAIN"`
3. `RUN`

## Files

| File | Purpose |
| ---- | ------- |
| `TERRAIN.HBA` | Hunter BASIC source — terrain profiler V1.0 |
| `asc2contour.py` | Python — converts OS Terrain 50 .asc grids to CONTOUR.DAT |
| `CONTOUR.DAT` | Contour dataset — TQ00 (North Downs, 10x10 km), development/limited area, production settings `-i 10 -s 200 -m 10` |
| `HUNTER_BASIC_GOTCHAS.md` | Hunter BASIC syntax differences discovered during hardware testing |
| `README.md` | This file |

### Subdirectories

| Directory | Contents |
| --------- | -------- |
| `Test/` | MBASIC test version (TERRTEST.BAS) with test README |

## Data Pipeline

```
OS Terrain 50 (.asc)  →  asc2contour.py  →  CONTOUR.DAT  →  Hunter RAM-disk
   50m grid               marching squares     contour         ready for
   spot heights           + Douglas-Peucker    polylines       link analysis
```

`asc2contour.py` is pure Python with no external dependencies. Accepts .asc files, .zip archives, or directories.

**OS Terrain 50** — free open data from Ordnance Survey: https://osdatahub.os.uk/downloads/open/Terrain50 (Open Government Licence v3.0). Download the grid squares covering your operational area.

| Flag | Default | Purpose |
|------|---------|---------|
| `-i` | 10 | Contour interval in metres |
| `-o` | CONTOUR.DAT | Output filename |
| `-s` | 50 | Douglas-Peucker simplification tolerance in metres |
| `-m` | 2 | Minimum vertices per contour segment |

Typical usage:

```
python asc2contour.py TQ00.asc TQ01.asc TQ10.asc TQ11.asc -i 10 -s 200 -m 10 -o AREA.DAT
```

## Testing

`Test/TERRTEST.BAS` is an MBASIC-compatible version that replaces Hunter pixel graphics with 78x20 ASCII art. Runs on any CP/M system with Z80 BASIC 4.7b. Includes a "Dump Profile Data" option for numerical verification of the intersection solver.

See `Test/README.md` for test coordinates and expected results.

See `HUNTER_BASIC_GOTCHAS.md` for all Hunter BASIC syntax differences discovered during hardware testing.

## License

MIT License. See [LICENSE](LICENSE) for details.

OS Terrain 50 data is provided under the Open Government Licence v3.0.