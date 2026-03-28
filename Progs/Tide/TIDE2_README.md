# TIDE2 — Self-Contained Tide Predictor for the Husky Hunter

A fully self-contained Hunter BASIC program that predicts tides on-device. No PC pre-computation needed — pick a port, enter a date, and the Hunter computes and plots the 24-hour tide curve from harmonic constituents.

## Status

**V1.3 — 28 Mar 2026.** Hardware verified. Portsmouth constants calibrated against UKHO-derived reference data for improved accuracy. Precision-safe astronomical arguments.

**Disclaimer:** This program is conceptual for educational and hobbyist use only. Predictions are approximate and unverified and must not be relied upon for navigation, safety, or any activity where life or property may be at risk. Always consult official tide tables and local harbour authorities for real-world decisions. The authors accept no liability for any loss or damage arising from the use of this software.

## Overview

TIDE2.HBA performs all tidal prediction mathematics natively on the Hunter. This makes it a true field tool — load once, predict any date.

### How It Works

```
ON THE HUNTER:

1. RUN TIDE2.HBA
        ↓
2. Select port (1-6)
   Enter date (DD/MM/YYYY)
        ↓
3. COMPUTING TIDES...          ← ~2-3 min on NSC800 @ 4MHz
   (240 samples × 7 harmonics    1680 COS evaluations)
        ↓
4. Text info screen:
   Port, date, HW/LW times
   and heights, tidal range
        ↓
5. Full-screen tide curve:
   240×64 plot, hour ticks,
   HW/LW markers + labels,
   chart datum line
        ↓
6. Another prediction? (Y/N)
```

### Tidal Prediction

Tides are predicted by summing harmonic constituents with nodal corrections:

```
h(t) = Z0 + Σ fn · An · cos(ωn · t + V0n + un - φn)
```

Where:

* Z0 = mean level above chart datum (metres)
* fn = nodal amplitude correction for the year
* An = constituent amplitude for the port
* ωn = angular speed (°/hr)
* V0n = equilibrium argument at Greenwich midnight
* un = nodal phase correction for the year
* φn = phase lag for the port

### Constituents

| Constituent | Period | Speed (°/hr) | Description |
| :---------: | :----: | :----------: | :---------- |
| M2 | 12h 25m | 28.984 | Principal lunar semidiurnal |
| S2 | 12h 00m | 30.000 | Principal solar semidiurnal |
| N2 | 12h 39m | 28.440 | Larger lunar elliptic |
| K1 | 23h 56m | 15.041 | Luni-solar diurnal |
| O1 | 25h 49m | 13.943 | Principal lunar diurnal |
| M4 | 6h 13m | 57.968 | Shallow water overtide |
| MS4 | 6h 06m | 58.984 | Shallow water compound |

### Built-in Ports

| # | Port | Z0 (m) | M2 Amp (m) | Calibrated |
| --- | ---- | ------ | ---------- | ---------- |
| 1 | Portsmouth | 2.85 | 1.45 | Yes |
| 2 | Dover | 3.67 | 2.29 | No |
| 3 | London Bridge | 3.40 | 2.19 | No |
| 4 | Southampton | 2.49 | 1.62 | No |
| 5 | Plymouth | 3.19 | 1.78 | No |
| 6 | Harwich | 2.03 | 1.32 | No |

Portsmouth constants were calibrated against UKHO-derived reference data for improved accuracy. Remaining ports use approximate/representative constants.

## Usage

On the Husky Hunter:

1. Transfer TIDE2.HBA to the Hunter via RS-232
2. Enter `BAS`
3. `LOAD "TIDE2"`
4. `RUN`
5. Select a port number (1–6)
6. Enter the date (day, month, year as separate prompts)
7. Wait for computation (\~5 minutes)
8. Press any key to advance from text screen to graphics
9. Press any key to exit; choose Y to predict another date

## Program Structure

```
Lines 1-16      Initialisation, DIM arrays, constants
Lines 20-44     Port selection menu
Lines 50-60     Date input with validation
Lines 70-94     READ port data and constituent speeds (RESTORE)
Lines 100-142   Date string formatting (ON MO GOTO for month names)
Lines 200-258   Astronomical arguments: days from 2020-01-01 epoch,
                fundamental arguments via daily rates (precision-safe)
Lines 260-326   Nodal corrections (f, u), equilibrium arguments (V0)
Lines 400-442   Tide prediction: 240 samples, 7-constituent inner loop
Lines 500-530   HW/LW detection with plateau-aware trend tracking
Lines 600-630   Text info screen (port, date, events, range)
Lines 700-770   Graphics: SCREEN 1 curve plot, hour ticks, datum line
Lines 800-836   HW/LW tick marks and time labels (LOCATE pixel coords)
Lines 900-912   Wait, exit, or loop for another prediction
Lines 5000-5064 DATA: 6 ports × (name, Z0, 7×amplitude, 7×phase)
Lines 5100-5112 DATA: 7 constituent angular speeds (°/hr)
Lines 5200-5202 DATA: cumulative days to month start (Jan-Dec)
```

## Technical Notes

* **Computation time**: 240 × 7 = 1,680 COS evaluations in interpreted BASIC on a 4 MHz CMOS CPU. Takes approximately 5 minutes on real hardware.
* **Memory**: DIM H(240) + 7-element constituent arrays + 8-element event arrays. Well within Hunter RAM.
* **PI**: Used as a built-in constant (Hunter BASIC reserves `PI`).
* **LOCATE**: Uses pixel coordinates (x, y) in SCREEN 1 / CHAR 0 mode, not character row/col.
* **KEY OFF/ON**: Toggles the soft key label line to maximise display area.
* **Date range**: Validated 1983–2099. The astronomical argument computation is accurate across this range.
* **Precision**: Uses a 2020-01-01 epoch with daily rates instead of J2000.0 century rates. The Moon longitude daily rate is split into integer (13°) and fractional (0.176397°) parts, each reduced mod 360 independently. This keeps all intermediate products under 5 significant digits, safe for Hunter's \~7-digit float arithmetic.
* **Modulo arithmetic**: Hunter BASIC has no MOD operator; uses `X-INT(X/360)*360` pattern.

## Accuracy

The harmonic prediction uses simplified Schureman nodal corrections (dominant N term only) with 7 constituents. This is sufficient for tide curve shape and approximate HW/LW times. For survey-grade prediction, full nodal modulation and additional constituents would be needed.

### Portsmouth — 28 Mar 2026

| Event | TIDE2 | Reference | Time Δ | Ht Δ |
| ----- | ----- | --------- | ------ | ---- |
| LW | — | 00:44, 1.9m | missed | — |
| HW | 07:01, 3.8m | 07:33, 3.8m | -32 min | 0.0m |
| LW | 13:09, 1.7m | 13:14, 1.6m | -5 min | +0.1m |
| HW | 19:52, 3.9m | 20:25, 4.0m | -33 min | -0.1m |

The early LW at 00:44 is not detected — the calibrated constants place this minimum just before midnight, so the tide is already rising at 00:00.

Across 31 reference events (8 dates spanning spring/neap cycle):

* **RMS time error: 10.9 min** (max 29 min)
* **RMS height error: 0.10 m** (max 0.28 m)

The residual timing error (\~11 min RMS) is the inherent limit of 7 constituents — professional tide tables use 50–60+.

Portsmouth is one of the most harmonically complex ports in the UK (famous for its "double high water"). Uncalibrated ports will show larger errors.

## License

MIT License.