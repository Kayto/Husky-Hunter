# TERRTEST — MBASIC Test Version

## Overview

Text-mode test version of TERRAIN.HBA for debugging and validation on any CP/M system running MBASIC (Z80 BASIC 4.7b). Replaces Hunter-specific graphics with ASCII art profile plots.

## Differences from TERRAIN.HBA

| Feature | TERRAIN.HBA (Hunter) | TERRTEST.BAS (MBASIC) |
|---------|---------------------|----------------------|
| Graphics | SCREEN 1, 240x64 pixel LCD | 78x20 character ASCII art |
| Terrain plot | `POINT x,y` pixel plotting | `#` characters in string grid |
| LOS line | Dashed pixels (every other) | `.` characters (every other) |
| Antenna masts | Vertical pixel lines | `\|` characters |
| Clear screen | `CHR$(1)` (Hunter) | `CHR$(26)` (CP/M) |
| dB overlay | `LOCATE 4,16` on graphics | Text line below plot |
| Power-off inhibit | `POKE 63416/63419` | Removed |
| Wait for key | `INKEY$` loop | `INPUT` prompt |
| Extra menu | — | Option 3: Dump Profile Data |

## Running

```
B>MBASIC TERRTEST
RUN
```

CONTOUR.DAT defaults to `J:CONTOUR.DAT` — change at the Load Area prompt or edit line 118.

## Menu

```
  TERRAIN PROFILER V1.0 (TEST)

Area: J:CONTOUR.DAT

1. Load Area
2. Link Analysis
3. Dump Profile Data
4. Exit

?
```

**Option 3 (Dump Profile Data)** prints all extracted profile points as a table — useful for verifying the intersection solver:

```
Profile:  21  points
TX ground:  130 m  RX ground:  130 m
Distance:   21.00 km

 # Chainage(km) Height(m)
-- ------------ ---------
 1      0.00      130.0
 2      0.71      130.0
 3      1.43      150.0
...
```

## Test Data

### Sample CONTOUR.DAT (synthetic)

The default sample in the parent directory has a double-ridge terrain (30x30 km). Origin 4000,3000.

| Test | Start | End | Expected |
|------|-------|-----|----------|
| Both ridges | `4010,3150` | `4220,3150` | BLOCKED (110m), ~120 dB |
| Short clear | `4010,3150` | `4040,3150` | CLEAR |

### Real Terrain — TQ00 (North Downs)

Generated from OS Terrain 50 with: `python asc2contour.py TQ00.asc -i 10 -s 50`

Area origin 5000,1000, size 100x100 hm (10x10 km). Elevation -1.7 to 168.5m.

CONTOUR.DAT uses delta encoding — first vertex absolute, subsequent vertices as deltas.

### Contour Data

The root `CONTOUR.DAT` is generated at **recommended production settings** (`-i 10 -s 200 -m 10`) but currently covers a **single development/limited area** — one 10x10 km OS Terrain 50 tile (TQ00, North Downs). Larger operational areas (up to 50x50 km / 25 tiles) can be generated with `asc2contour.py`.

| Setting | Value | Rationale |
|---------|-------|-----------|
| Interval | 10m | Captures terrain features that 20m misses — a 15m ridge between contours would be invisible but can block a radio link |
| Simplify | 200m | Douglas-Peucker tolerance — preserves shape while reducing vertices |
| Min vertices | 10 | Removes tiny hilltop loops too small to intersect a bearing line |

Result: 22 segments, 391 vertices, 2.7 KB for TQ00 (10x10 km). See `Test/contour_comparison.png` for a visual comparison of full vs production resolution.

Load via menu option 1 — default is `J:CONTOUR.DAT`.

Terrain layout: flat near sea level in the south, rising northward to 160m summits (North Downs escarpment). Isolated 80m hill in the SE.

#### Clear LOS

| Test | Start | End | Terrain |
|------|-------|-----|---------|
| Flat south | `5015,1008` | `5064,1014` | ~0m flat strip |
| Gentle slope | `5070,1050` | `5080,1060` | Uniform 30-40m slope |

#### Blocked LOS

| Test | Start | End | Terrain |
|------|-------|-----|---------|
| Central hillock | `5022,1063` | `5040,1063` | 40m hillock between 15m points |
| SE isolated hill | `5080,1043` | `5099,1043` | 80m hill between 35m points |

## ASCII Profile Output

Example (synthetic double-ridge, `4010,3150` → `4220,3150`):

```
TX                                                                          RX
|                                                                              |
|                        ##                    ###                             |
|                       #  ##                ##   ##                           |
|                      #     ##             #       ##                         |
|                     #        #          ##          #                        |
|                    #          #        #             #                       |
|                   #            ##    ##               ##                     |
|                 ##               # ##                   #                    |
|                #                  #                      ##                  |
|              ##                                            ###               |
|            ##                                                 ##             |
|           #                                                     #            |
|         ##                                                       ##          |
|        #                                                           #         |
|       #                                                             ##       |
|     ##                                                                ##     |
|| .#. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .#. .||
||##                                                                        ##||
|                                                                              |
+------------------------------------------------------------------------------+
Dist:  21  km  Loss:  120  dB  LOS: BLOCKED ( 110 m)
```

## Files

| File | Purpose |
|------|---------|
| `TERRTEST.BAS` | MBASIC test version of terrain profiler (ASCII format) |
| `contour_comparison.png` | Visual comparison of full vs production contour resolution |
| `README.md` | This file |

## License

MIT License. See [LICENSE](../LICENSE) for details.
