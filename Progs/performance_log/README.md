# PC Performance Logger for the Husky Hunter

Real-time PC CPU and memory usage display on the Hunter's 240×64 LCD, fed over RS-232.

## Status

**v1.0 — Working.** In development to tighten line feed parsing and screen refresh optimisations.

## Overview

### Workflow

```
PC (running):                          Hunter (displaying):

feed.py                                RUN STRIP.HBA
  reads CPU% + MEM%                          ↓
  every ~1 second                      Waits for serial data
        ↓                                    ↓
  sends CPU then MEM                   Receives values via LINPUT
  as separate lines                          ↓
  over RS-232 @ 4800 baud             Displays current values,
        ↓                              clears and refreshes
  repeats...
```

### Display Layout (text mode, 40×8)

```
┌────────────────────────────────────────┐
│PC Performance Logger                   │  ← Row 0: title
│                                        │  ← Row 1: blank
│CPU: 23%                                │  ← Row 2: CPU value
│MEM: 61%                                │  ← Row 3: MEM value
└────────────────────────────────────────┘
```

Refreshes on each sample. Screen cleared with `CHR$(1)` between updates.

### Serial Protocol

Two separate ASCII lines per sample:

```
CPU\r\n
MEM\r\n
```

- CPU = integer 0-100 (percent)
- MEM = integer 0-100 (percent)
- Example: `23\r\n` then `61\r\n`
- Rate: ~1 sample/second
- Baud: 4800, 8N1

Hunter reads each value with `LINPUT "",var` (dedicated RS-232 input, suppressed prompt).

## Files

| File | Description |
|------|-------------|
| `feed.py` | PC-side Python script — reads CPU/MEM, sends over serial |
| `feed.bat` | Windows batch launcher for feed.py (double-click to start) |
| `LOG.HBA` | Hunter BASIC display program |

## Usage

### PC Side

```bash
# List available COM ports
python feed.py --list

# Start feeding on COM8
python feed.py -p COM8

# Custom port and interval
python feed.py -p COM3 -i 2.0
```

Or double-click `feed.bat` (defaults to COM8, 1s interval):

```
feed.bat [COMx] [interval]
```

To use a different COM port, pass it as the `-p` argument to `feed.py` or the first argument to `feed.bat`. Edit the default in `feed.bat` (line `set PORT=COM8`) to change permanently.

### Hunter Side

1. Connect RS-232 cable between PC and Hunter
2. On Hunter: `BAS`, `LOAD "LOG"`, `RUN`
3. Start feed on PC
4. Press BREAK on Hunter to exit

## Requirements

PC: Python 3, `psutil`, `pyserial`

```bash
pip install psutil pyserial
```

## The Husky Hunter

Ruggedised portable field computer (1983). NSC800-4 @ 4 MHz, 240×64 dot LCD, RS-232 @ 4800 baud, DEMOS 2.2 (CP/M 2.2 derivative).

## License

MIT License.
