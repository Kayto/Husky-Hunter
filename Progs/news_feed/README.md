# BBC News Feed for the Husky Hunter

Displays BBC News headlines on the Hunter's 240×64 LCD, fed from PC over RS-232.

## Status

**v1.0 — Working.** In development to tighten line feed parsing and screen refresh optimisations.

## Overview

### Workflow

```
PC (running):                          Hunter (displaying):

feed.py                                RUN NEWS.HBA
  fetches BBC News RSS feed                  ↓
  formats to 40 columns               Waits for serial data
        ↓                                    ↓
  sends 8 pre-formatted lines         Receives lines via LINPUT
  per headline over RS-232                   ↓
        ↓                              Clears screen, displays
  next headline every ~15s              headline + description
        ↓                                    ↓
  re-fetches on cycle complete         Loops for next headline
```

### Display Layout (40×8 text)

```
┌────────────────────────────────────────┐
│BBC News                          1/30 │  ← header + counter
│----------------------------------------│  ← separator
│Potential Houthi threat to Red          │  ← title (word-wrapped,
│Sea shipping could further              │     up to 3 lines)
│damage global economy                   │
│                                        │  ← blank separator
│The Iran-backed group could bring       │  ← description (up to
│a second crucial waterway to...         │     2 lines, truncated)
└────────────────────────────────────────┘
```

### Serial Protocol

8 ASCII lines per headline, each CR+LF terminated:

1. Header: `BBC News` + item counter
2. Separator: `----------------------------------------`
3–5. Title (word-wrapped to 40 chars, padded to 3 lines)
6. Blank line
7–8. Description (word-wrapped, truncated with `...`)

Hunter reads with `LINPUT "",L$(I)` (suppressed prompt, dedicated RS-232 input).

The PC pre-wraps all text to 40 columns and sanitises Unicode (curly quotes, dashes, ellipsis) to ASCII.

## Files

| File | Description |
|------|-------------|
| `feed.py` | PC-side Python script — fetches RSS, sends formatted headlines |
| `feed.bat` | Windows batch launcher (double-click to start) |
| `NEWS.HBA` | Hunter BASIC headline display program |

## Usage

### PC Side

```bash
# List available COM ports
python feed.py --list

# Start feeding on COM8 (default 15s per headline)
python feed.py -p COM8

# Faster rotation
python feed.py -p COM8 -i 10

# Different RSS feed
python feed.py -p COM8 -u "https://example.com/other/feed.xml"
```

Or double-click `feed.bat` (defaults to COM8, 15s):

```
feed.bat [COMx] [interval]
```

To use a different COM port, pass it as the `-p` argument to `feed.py` or the first argument to `feed.bat`. Edit the default in `feed.bat` (line `set PORT=COM8`) to change permanently.

### Hunter Side

1. Connect RS-232 cable between PC and Hunter
2. On Hunter: `BAS`, `LOAD "NEWS"`, `RUN`
3. Start feed on PC
4. Press BREAK on Hunter to exit

## Requirements

PC: Python 3, `pyserial`

```bash
pip install pyserial
```

RSS parsing uses Python stdlib only (`urllib` + `xml.etree`).

## Demo

[newsfeed.mp4](../images/newsfeed.mp4)

## The Husky Hunter

Ruggedised portable field computer (1983). NSC800-4 @ 4 MHz, 240×64 dot LCD, RS-232 @ 4800 baud, DEMOS 2.2 (CP/M 2.2 derivative).
