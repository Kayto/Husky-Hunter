# Husky Hunter BASIC — Quirks & Gotchas

Reference for differences from MBASIC/GW-BASIC, discovered through
hardware testing on a Husky Hunter (DEMOS 2.2, V09F ROM).

---

## Reserved Words / Built-in Constants

| Word | Type | Trap |
|------|------|------|
| `PI` | Built-in constant (3.14159) | **Cannot assign to it.** `PI=3.14` causes `*STX Error`. Use the built-in value directly. |
| `LN` | Function (natural logarithm) | **Cannot use as a variable name.** `LN=LOG(10)` causes `*STX Error`. Rename to e.g. `L0`. |
| `LOG` | Function (log base 10) | **Reversed from MBASIC** where LOG = natural log. Hunter: `LOG(10)` = 1.0, `LN(10)` = 2.302... |

> **Tip:** If you get an unexplained `*STX Error`, check whether any variable
> name on that line matches a Hunter BASIC keyword or function. The full
> function list is in manual §5.1 (pages 5-1 to 5-4).

---

## File I/O Syntax

Hunter BASIC file I/O is **not** MBASIC-compatible. Key differences:

### OPEN
```basic
' MBASIC (WRONG on Hunter):
OPEN "I",#1,"DATA.TXT"

' Hunter BASIC (CORRECT):
OPEN "DATA.TXT" FOR INPUT AS #1
OPEN "DATA.TXT" FOR OUTPUT AS #1
```

### INPUT from file
```basic
' MBASIC (WRONG on Hunter):
INPUT #1,A,B,C

' Hunter BASIC (CORRECT) — no space, # directly after INPUT:
INPUT#1,A,B,C
```

### WRITE to file
```basic
' MBASIC (WRONG):
WRITE #1,A,B,C

' Hunter BASIC (CORRECT):
WRITE#1,A,B,C
```

### CLOSE
```basic
' MBASIC (WRONG):
CLOSE #1

' Hunter BASIC (CORRECT) — no space:
CLOSE#1
CLOSE#1,#2,#3
```

### Data file string quoting

When mixing string and numeric values on the same line in a data file,
**strings must be enclosed in double quotes** or `INPUT#` will misparse:

```
WRONG:   A,5000,1000,100,100
CORRECT: "A",5000,1000,100,100
```

Without quotes, `INPUT#1,A$,V1,V2` may read the entire line into `A$`,
throwing all subsequent reads off. Symptoms: `?REDO FROM START` messages
followed by `*IPE Error` (Input Past End).

Use `WRITE#` to create data files — it automatically quotes strings.

> **Manual refs:** §4.13 File Handling, §5.10.9 INPUT#, §5.17.13 PRINT#

### BAS LOAD and programs

`.HBA` files transferred to the Hunter (e.g. via HCOM) display correctly
when checked with CP/M `TYPE`. The file checks OK on disk, but `LOAD`
inside BAS can corrupt it — line 10 of HIMAGE.HBA was affected (quirk?).
Retyping the affected line fixed it.

`,A` flag is **not** supported (`LOAD "file",A` gives `*STX Error`).

**Alternative:** Send the file via RS-232 while in BAS, so each numbered
line is entered directly by the interpreter.

---

## Error Codes

Hunter BASIC errors are 3-character codes (§4.14, page 4-47):

| Code | # | Meaning | Common Cause |
|------|---|---------|-------------|
| STX | 2 | Syntax Error | Reserved word used as variable; wrong statement syntax |
| DIM | 6 | Dimension Error | Re-running program without `NEW` — arrays already exist |
| FP | 7 | Floating Point Error | Division by zero |
| LNo | 8 | Line Number Error | GOTO/GOSUB to non-existent line |
| MAG | 10 | Magnitude Error | Array index > DIM size |
| MEM | 12 | Storage Overflow | Out of memory |
| TYP | 15 | Type Mismatch | String where number expected (or vice versa) |
| FNF | 18 | File Not Found | Filename wrong or file doesn't exist |
| FOP | 20 | File Already Open | Forgot to CLOSE before re-opening |
| RD | — | Read Data Error | READ past end of DATA — no more DATA values available |
| DSK | 26 | Disk Access Error | File system problem |

> **The DIM Error trap:** If a program crashes mid-run, arrays from the
> partial execution still exist. Running again hits `*DIM Error` on the
> DIM statement. **Always type `NEW` before reloading after a crash.**

---

## Power-Off Inhibit

```basic
POKE 63416,1:POKE 63419,1   ' Disable power-off button
POKE 63416,0:POKE 63419,0   ' Re-enable power-off button
```

Memory locations F7B8H (63416) and F7BBH (63419) control power-off.
Setting to 1 prevents the power button from turning the unit off.

**DANGER:** If your program POKEs these to inhibit power-off and then
crashes, the power button **will not work**. The Hunter appears stuck.

**Recovery:** At the BASIC prompt, type:
```
POKE 63416,0:POKE 63419,0
```

If you can't get to the prompt, remove the battery to force a reset.

> **Best practice:** Add `ON ERROR` handling that restores these POKEs,
> or avoid inhibiting power-off during development/debugging.

---

## Serial Port (RS-232)

| Setting | Memory Address | Default | Notes |
|---------|---------------|---------|-------|
| Baud rate | 63480 (F7E8H) | 6 (1200 baud) | Values: 4=300, 5=600, 6=1200, 7=2400, 9=4800 |
| Parity | 63487 | 0 (none) | |
| Parity type | 63488 | 0 | |
| XON/XOFF | 63482 | — | POKE 0 to disable |
| CTS | 63483 | — | POKE 0 to disable |
| DSR | 63485 | — | POKE 0 to disable |
| DCD | 63486 | — | POKE 0 to disable |

- **Pinout:** Standard DTE on DB25 (pin 2 = TX, pin 3 = RX)
- **Voltage levels:** True RS-232 (±5-9V via INVCON circuit) — **not TTL**
- **Connection to PC:** Requires USB-to-RS232 cable + **null modem** adapter
  (two DTE devices need TX↔RX crossover)
- **TTL FTDI breakout boards will NOT work** — voltage mismatch

---

## Graphics

- `SCREEN 0` = text mode, `SCREEN 1` = graphics mode (240×64 pixels)
- **`POINT(x,y)` reads a pixel state** — it is a function, NOT a drawing command
- **`PSET(x,y)` sets a pixel** (turns it black) — parentheses required
- `PRESET(x,y)` resets a pixel (turns it white)
- `LINE (x1,y1)-(x2,y2)` draws a line (if available in ROM version)
- Origin (0,0) = **top-left corner**
- `LOCATE row,col` positions text cursor (in text mode)
- `CHR$(1)` = clear screen (Hunter-specific, not standard CLS in all contexts)

> **POINT vs PSET trap:** Using `POINT x,y` to draw pixels (as in MBASIC)
> will cause `*STX Error`. Hunter BASIC uses `PSET(x,y)` with parentheses
> to set pixels. `POINT(x,y)` returns pixel state only.

---

## Miscellaneous

- **Max files:** Default MAXFILES is 1. Set `MAXFILES=n` before opening
  multiple files.
- **`NEW` clears everything:** Variables, arrays, and the program. Use it
  before loading a new program after a crash.
- **`REM` vs `'`:** Apostrophe works as REM and doesn't need a colon
  separator: `10 X=X+1' comment` saves a byte vs `10 X=X+1:REM comment`
- **CALL / ARG / PUSH / POP:** Machine code interface. ARG loads E and C
  registers with a 16-bit value. PUSH/POP for the linkage stack.
- **EOF(n):** Returns -1 at end of file, 0 if more data. Same as MBASIC.
- **EOF and CP/M record padding:** CP/M pads files to 128-byte record
  boundaries. `EOF(n)` may not trigger until a read actually fails on
  the padding bytes. Use `ON ERROR GOTO` to catch `*IPE Error` at end
  of file as a safety net:
  ```basic
  ON ERROR GOTO 500
  ...
  500 RESUME 600
  600 ON ERROR GOTO 0
  601 CLOSE#1
  ```
- **`INPUT#` reads one line per call:** Each `INPUT#1,A,B,C` reads one
  line and distributes comma-delimited fields to variables. Extra fields
  on the line produce `?extra ignored`. Missing fields cause `?REDO from
  start` and re-read. It does NOT read across line boundaries.

---

## Verification Status

| Item | Status |
|------|--------|
| PI is reserved / cannot assign | **Confirmed** on hardware (STX Error) |
| LN is reserved | **Confirmed** on hardware (STX Error) |
| LOG = log base 10 (not natural log) | From manual — not yet tested |
| OPEN syntax (`FOR INPUT AS #n`) | **Confirmed** on hardware (file reads work) |
| INPUT# syntax (no space) | **Confirmed** on hardware (file reads work) |
| CLOSE# syntax (no space) | **Confirmed** on hardware (file reads work) |
| String quoting in data files | **Confirmed** — quoted strings parse correctly |
| INPUT# reads one line per call | **Confirmed** — extra fields give `?extra ignored` |
| EOF unreliable at end of file | **Confirmed** — CP/M record padding causes false reads |
| POINT vs PSET for drawing | **Confirmed** on hardware (STX Error using POINT) |
| PSET(x,y) draws pixels | **Confirmed** on hardware (terrain profile plotted) |
| LOAD works with ASCII .HBA files | **Confirmed** — minor corruption at line 10 (quirk?), `,A` not supported |
| Power-off POKE inhibit | **Confirmed** on hardware (stuck power button) |
| Power-off POKE recovery | **Confirmed** on hardware |
| DIM Error after crash / need NEW | **Confirmed** on hardware |
| Serial port settings / addresses | From manual + partial hardware testing |
| RS-232 voltage levels (not TTL) | From manual / ROM analysis — not scope-verified |

> **TERRAIN.HBA partially working on hardware** (March 2026). Menu, file
> loading, contour extraction, and profile plotting confirmed. LOS line,
> dB calculation, and some refinements still in progress.
>
> **HIMAGE.HBA confirmed working** (March 2026). Full 240×64 image renders
> correctly when sent via serial to BASIC interactive mode.

*Last updated: March 2026*
*Source: Husky Hunter Manual V09F 1984 + hardware testing*
