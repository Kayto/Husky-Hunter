# Performance File Logger for the Husky Hunter

Logs PC CPU and memory usage to a file on the Hunter, with readback display.

## Status

**v1.0 — Working.** In development to tighten line feed parsing and screen refresh optimisations.

## Overview

Based on the [performance_log](../performance_log/) project, this adds file logging on the Hunter side. Received samples are written to `PERFLOG.DAT` on the Hunter's DEMOS filesystem and can be read back later.

### Workflow

```
PC (running):                          Hunter (displaying):

feed.py                                RUN LOGF.HBA
  reads CPU% + MEM%                          ↓
  every ~1 second                      Menu: 1) Log  2) Read
        ↓                                    ↓
  sends CPU then MEM                   Option 1: receives data,
  as separate lines                     displays + writes to
  over RS-232 @ 4800 baud              PERFLOG.DAT
        ↓                              BREAK key stops + saves
  repeats...                                 ↓
                                        Option 2: reads back
                                         PERFLOG.DAT, pages
                                         through samples
```

### Display — Log Mode

```
┌────────────────────────────────────────┐
│Logging  #42                            │  ← sample counter
│                                        │
│CPU: 23%                                │  ← latest CPU
│MEM: 61%                                │  ← latest MEM
│                                        │
│BREAK to stop + save                    │
└────────────────────────────────────────┘
```

### Display — Read Mode

```
┌────────────────────────────────────────┐
│Reading PERFLOG.DAT                     │
│--------------------                    │
│#1 CPU:23% MEM:61%                      │
│#2 CPU:45% MEM:62%                      │
│#3 CPU:12% MEM:60%                      │
│#4 CPU:67% MEM:63%                      │
│#5 CPU:34% MEM:61%                      │
│--- any key ---                         │  ← pages every 5 rows
└────────────────────────────────────────┘
```

### File Format (PERFLOG.DAT)

Sequential text file, one record per line:

```
 1 , 23 , 61
 2 , 45 , 62
 3 , 12 , 60
```

Fields: sample number, CPU%, MEM%. Written with `PRINT#1` and read back with `INPUT#1`.

### Serial Protocol

Same as performance_log — two separate ASCII lines per sample:

```
CPU\r\n
MEM\r\n
```

- Baud: 4800, 8N1
- Rate: ~1 sample/second

## Files

| File | Description |
|------|-------------|
| `feed.py` | PC-side Python script — reads CPU/MEM, sends over serial |
| `feed.bat` | Windows batch launcher (double-click to start) |
| `LOGF.HBA` | Hunter BASIC logger with file write + readback |

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
2. On Hunter: `BAS`, `LOAD "LOGF"`, `RUN`
3. Choose option **1** to start logging
4. Start feed on PC
5. Press **BREAK** on Hunter to stop logging (file is saved)
6. `RUN` again, choose option **2** to read back the log

**Note:** Option 1 creates a new `PERFLOG.DAT` each time (overwrites previous). The file persists on the Hunter's DEMOS filesystem until overwritten or deleted.

## Requirements

PC: Python 3, `psutil`, `pyserial`

```bash
pip install psutil pyserial
```

## The Husky Hunter

Ruggedised portable field computer (1983). NSC800-4 @ 4 MHz, 240×64 dot LCD, RS-232 @ 4800 baud, DEMOS 2.2 (CP/M 2.2 derivative).
