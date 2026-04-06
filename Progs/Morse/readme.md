# Morse Code Tape for the Husky Hunter

Type a message, press ENTER, and watch Morse code scroll across the LCD like a paper tape reader with audio output.

## Status

**v1.0 — Working.**

## Overview

Supports A-Z, 0-9 and space. Morse patterns stored as DATA strings (`1`=dot, `2`=dash). Audio via `SOUND 80,duration` — pitch 80 ≈ 784 Hz (G5). Standard ITU timing: 1-unit dot, 3-unit dash, 1-unit element gap, 3-unit character gap, 7-unit word gap.

### Display Layout

```
┌────────────────────────────────────────┐
│MORSE CODE TAPE                         │  ← title
│================================        │  ← separator
│                                        │
│Message (ENTER=send ESC=quit):          │  ← prompt
│? HELLO                                 │  ← user input
│                                        │
│Transmitting...                         │
│                                        │
│*...*...*...*..---...*.*..*..---..---.. │  ← tape output
└────────────────────────────────────────┘
```

Dot = `*`, Dash = `---`, Baseline = `.` (gaps between elements/characters/words). Audio tone plays for the full duration of each element. Screen scrolls continuously.

## Files

| File | Description |
|------|-------------|
| `MORSE.BAS` | Hunter BASIC Morse code tape program |

## Usage

1. On Hunter: `BAS`, `LOAD "MORSE"`, `RUN`
2. Type a message at the prompt
3. Press ENTER to transmit — watch and hear the Morse code scroll across the screen
4. Enter another message or press ENTER with no input to exit

## Technical Notes

- Morse patterns stored as DATA strings: `1`=dot, `2`=dash (e.g. `"12"` = A = `.-`)
- Audio via `SOUND 80,duration` — pitch 80 = ~784 Hz (G5)
- Dot duration = 60, dash = 180 (3× dot)
- Screen scrolls continuously, wrapping row counter at 8 rows

## The Husky Hunter

Ruggedised portable field computer (1983). NSC800-4 @ 4 MHz, 240×64 dot LCD, RS-232 @ 4800 baud, DEMOS 2.2 (CP/M 2.2 derivative).