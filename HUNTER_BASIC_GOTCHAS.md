# Husky Hunter BASIC — Quirks & Gotchas

Reference for differences from MBASIC/GW-BASIC, discovered through
hardware testing on a Husky Hunter (DEMOS 2.2, V09F ROM). Some may be obvious if I spent more time reading the manuals :). Don't take all as definitive below, just use if you have problems.

- - -

## Contents

- [Reserved Words / Built-in Constants](#reserved-words--built-in-constants)
- [File I/O Syntax](#file-io-syntax)
  - [OPEN](#open)
  - [INPUT from file](#input-from-file)
  - [WRITE to file](#write-to-file)
  - [CLOSE](#close)
  - [Data file string quoting](#data-file-string-quoting)
  - [BAS LOAD and programs](#bas-load-and-programs)
- [Error Codes](#error-codes)
- [Hard Reset (Lockup Recovery)](#hard-reset-lockup-recovery)
- [Power-Off Inhibit](#power-off-inhibit)
- [Battery & Power Consumption](#battery--power-consumption)
  - [Use `INCHR` instead of `INKEY$` for key-press waits](#use-inchr-instead-of-inkey-for-key-press-waits)
- [Performance](#performance)
  - [Use `OPCHR` instead of `PRINT CHR$()`](#use-opchr-instead-of-print-chr)
- [Clean Exit — Restoring Display State](#clean-exit--restoring-display-state)
  - [What needs restoring](#what-needs-restoring)
  - [Recommended exit pattern](#recommended-exit-pattern)
  - [What happens if you don't clean up](#what-happens-if-you-dont-clean-up)
  - [BREAK exits dirty](#break-exits-dirty)
  - [RUN resets file handles](#run-resets-file-handles)
- [Serial Port (RS-232)](#serial-port-rs-232)
  - [LINPUT for RS-232 receive](#linput-for-rs-232-receive)
- [Graphics](#graphics)
- [Miscellaneous](#miscellaneous)
- [Verification Status](#verification-status-randomly-complete)

- - -

## Reserved Words / Built-in Constants

| Word | Type | Trap |
| ---- | ---- | ---- |
| `PI` | Built-in constant (3.14159) | **Cannot assign to it.** `PI=3.14` causes `*STX Error`. Use the built-in value directly. |
| `LN` | Function (natural logarithm) | **Cannot use as a variable name.** `LN=LOG(10)` causes `*STX Error`. Rename to e.g. `L0`. |
| `LOG` | Function (log base 10) | **Reversed from MBASIC** where LOG = natural log. Hunter: `LOG(10)` = 1.0, `LN(10)` = 2.302... |

> **Tip:** If you get an unexplained `*STX Error`, check whether any variable name on that line matches a Hunter BASIC keyword or function. The full function list is in manual §5.1 (pages 5-1 to 5-4).

- - -

## File I/O Syntax

Hunter BASIC file I/O is **not** MBASIC-compatible. Key differences:

### OPEN

``` basic
' MBASIC (WRONG on Hunter):
OPEN "I",#1,"DATA.TXT"

' Hunter BASIC (CORRECT):
OPEN "DATA.TXT" FOR INPUT AS #1
OPEN "DATA.TXT" FOR OUTPUT AS #1
```

### INPUT from file

``` basic
' MBASIC (WRONG on Hunter):
INPUT #1,A,B,C

' Hunter BASIC (CORRECT) — no space, # directly after INPUT:
INPUT#1,A,B,C
```

### WRITE to file

``` basic
' MBASIC (WRONG):
WRITE #1,A,B,C

' Hunter BASIC (CORRECT):
WRITE#1,A,B,C
```

### CLOSE

``` basic
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

`.HBA` files are plain ASCII text (numbered BASIC lines). They are
transferred to the Hunter via HCOM as-is and display correctly when
checked with CP/M `TYPE`. However, `LOAD` inside BAS has been observed to corrupt programs — line 10 of HIMAGE.HBA was garbled after `LOAD`
despite the file being intact on disk.

**Possible cause:**
Hunter BASIC `LOAD` may expect a tokenised or
intermediate format rather than raw ASCII. All `.HBA` files in this
project are plain ASCII text (numbered BASIC lines, CR+LF terminated).
The `.HBA` i use may not be in the correct format the Hunter natively recognises. `LOAD` may partially
work with ASCII files but misparse certain lines.

`,A` flag is **not** supported (`LOAD "file",A` gives `*STX Error`).

**Workaround:**
Send the file via RS-232 while in BAS, so each numbered
line is entered directly by the interpreter — this bypasses `LOAD`
entirely and avoids any format mismatch.

**For investigation:**
Analyse a Hunter side saved `.hba` versus my ASCII
based `.hba`. This should help identify the differences for consideration.

- - -

## Error Codes

Hunter BASIC errors are 3-character codes (§4.14, page 4-47):

| Code | # | Meaning | Common Cause |
| ---- | --- | ------- | ------------ |
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

> **The DIM Error trap:** If a program crashes mid-run, arrays from the partial execution still exist. Running again hits `*DIM Error` on the DIM statement. **Always type `NEW` before reloading after a crash.**

- - -

## Hard Reset (Lockup Recovery)

If the Hunter locks up due to bad code and cannot be interrupted normally:

1. Power off.
2. Power on while holding **Ctrl** and **C** simultaneously. The Hunter should beep twice.
3. Release all keys.
4. Enter the code **56580** — the Hunter should reboot.

> This bypasses the running program and forces a cold reset. Useful when a
> runaway loop or bad POKE makes the keyboard unresponsive.

- - -

## Power-Off Inhibit

``` basic
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

> **Best practice:** Add `ON ERROR` handling that restores these POKEs, or avoid inhibiting power-off during development/debugging.

- - -

## Battery & Power Consumption

### Use `INCHR` instead of `INKEY$` for key-press waits

``` basic
' BAD — burns battery: interpreter loops constantly
DO : WHILE INKEY$="" : WEND : LOOP

' GOOD — CPU drops to low-power mode until key arrives
INCHR,A
```

`INKEY$=""` keeps the BASIC interpreter executing continuously,
preventing the CPU from entering low-power mode. `INCHR,A` suspends
execution and lets the hardware wait for a keypress with the CPU mostly
idle. The screen stays on but current draw is significantly reduced.

**`INCHR` syntax (§5.10.3):**

```basic
INCHR varname               ' wait, no prompt — variable gets decimal ASCII value
INCHR "prompt";varname      ' wait with prompt string
INCHR,varname               ' wait, suppress ? prompt character
```

- The variable is **numeric** — it receives the decimal ASCII value of the
  key pressed (e.g. `A`=65).  Using a string variable (`K$`) causes `*STX Error`.
- Does not wait for ENTER — returns immediately on any single key.
- Escape returns 27.  SHIFT/HELP/CTRL/POWER return no value.

> **Rule of thumb:** any time you need to wait for user input, prefer
> `INCHR` over polling `INKEY$`.

- - -

## Performance

### Use `OPCHR` instead of `PRINT CHR$()`

Each BASIC statement is a separate token. Every call to `PRINT CHR$(n)`
requires the interpreter to process *two* tokens (`PRINT` and `CHR$`),
plus a function call, plus the numeric argument. `OPCHR` is a **single
token** that sends one or more raw character codes to the screen in one
pass:

``` basic
' SLOW — two tokens + function-call overhead, repeated per character:
PRINT CHR$(1) : PRINT CHR$(15) : PRINT CHR$(5) : PRINT CHR$(5)

' FAST — one token, all characters in a single statement:
OPCHR1,15,5,5
```

The example above clears the screen (`CHR$(1)`) then moves the cursor
to column 5, row 5 (`CHR$(15)` = cursor-position command, followed by
the X and Y coordinates).

`OPCHR` is especially worthwhile in loops or any code that draws to
the screen repeatedly.

- - -

## Clean Exit — Restoring Display State

Programs that change display mode, hide the cursor, or disable the
function key line **must restore them before ending**, otherwise the
Hunter is left in a broken state after BREAK or END.

### What needs restoring

| Init command | Cleanup command | What it does |
| ------------ | --------------- | ------------ |
| `SCREEN 1` | `SCREEN 0` | Return to text mode from graphics |
| `CUROFF` | `CURON` | Re-enable the text cursor |
| `KEY OFF` | `KEY ON` | Re-display the function key line |
| `PRINT CHR$(1);` | — | Clear screen (use during cleanup too) |

### Recommended exit pattern

Restore everything that was changed at init, in order:

``` basic
900 SCREEN 0:PRINT CHR$(1);:KEY ON:CURON:END
```

### What happens if you don't clean up

* **Missing `SCREEN 0`:** Hunter stays in graphics mode. Need to type `SCREEN 0`
blind at the BASIC prompt?
* **Missing `CURON`:** No visible cursor at the BASIC prompt. The
Hunter still accepts input, but you can't see where you're typing.
* **Missing `KEY ON`:** Function key labels disappear from the bottom
of the screen. Not critical but confusing.

### BREAK exits dirty

Programs that loop forever (e.g. NEWS.HBA, LOG.HBA) rely on BREAK to exit. BREAK does **not** run any cleanup code — it drops straight to the BASIC prompt with whatever display state was active. After pressing BREAK, if you have problems, manually type:

```
SCREEN 0:PRINT CHR$(1);:KEY ON:CURON
```

### RUN resets file handles

Looks like `RUN` closes all open file channels automatically. If a program has a file open (e.g. `OPEN "DATA" FOR OUTPUT AS #1`) and you press BREAK, typing `RUN` to restart will cleanly reset the file state — no `*FOP
Error`. Discovered with LOGF.HBA: BREAK during logging, then `RUN`
and selecting option 2 (read back) opens the file without error.

This means `GOTO` or `CONT` after BREAK **would** hit `*FOP Error`
(the channel is still open), but `RUN` is safe.

> **Best practice:** Match every `SCREEN 1`, `CUROFF`, and `KEY OFF`
> with a corresponding restore in an exit routine. For infinite-loop
> programs, manual cleanup may be needed after BREAK.

- - -

## Serial Port (RS-232)

| Setting | Memory Address | Default | Notes |
| ------- | -------------- | ------- | ----- |
| Baud rate | 63480 (F7E8H) | 6 (1200 baud) | Values: 4=300, 5=600, 6=1200, 7=2400, 9=4800 |
| Parity | 63487 | 0 (none) |  |
| Parity type | 63488 | 0 |  |
| XON/XOFF | 63482 | — | POKE 0 to disable |
| CTS | 63483 | — | POKE 0 to disable |
| DSR | 63485 | — | POKE 0 to disable |
| DCD | 63486 | — | POKE 0 to disable |

### LINPUT for RS-232 receive

``` basic
LINPUT "",A$   ' Read one line from RS-232, suppressed prompt
```

`LINPUT ""` suppresses the `?` prompt and reads a full line (up to CR)
from the serial port. This is the standard pattern for receiving
PC-fed data line-by-line (used in NEWS.HBA, LOG.HBA, TIDE2.HBA).

* <b>Not the same as `INPUT#`</b> — `INPUT#` reads from files, `LINPUT`
reads from the RS-232 port (or keyboard if no serial data).
* **Blocks until a line arrives** — the Hunter will sit and wait.
* **No timeout mechanism** — if the PC stops sending, the Hunter hangs.
Press BREAK to escape.
* **Pinout:** Standard DTE on DB25 (pin 2 = TX, pin 3 = RX)
* **Voltage levels:** True RS-232 (±5-9V via INVCON circuit) — **not TTL**
* **Connection to PC:** Requires USB-to-RS232 cable + **null modem** adapter
(two DTE devices need TX↔RX crossover)
* **TTL FTDI breakout boards will NOT work** — voltage mismatch

- - -

## Graphics

* `SCREEN 0` = text mode, `SCREEN 1` = graphics mode (240×64 pixels)
* **`POINT(x,y)` reads a pixel state** — it is a function, NOT a drawing command
* **`PSET(x,y)` sets a pixel** (turns it black) — parentheses required
* `PRESET(x,y)` resets a pixel (turns it white)
* `LINE (x1,y1)-(x2,y2)` draws a line (if available in ROM version)
* Origin (0,0) = **top-left corner**
* `LOCATE row,col` positions text cursor (in text mode)
* `CHR$(1)` = clear screen (Hunter-specific, not standard CLS in all contexts)

> **POINT vs PSET trap:** Using `POINT x,y` to draw pixels (as in MBASIC)
> will cause `*STX Error`. Hunter BASIC uses `PSET(x,y)` with parentheses
> to set pixels. `POINT(x,y)` returns pixel state only.

- - -

## Miscellaneous

* **`MOD` operator does not exist:** Hunter BASIC has no `MOD` keyword — using it causes `*STX Error`. Use `INT(A/B)` arithmetic instead: `M = A - INT(A/B)*B`
* **Max files:** Default MAXFILES is 1. Set `MAXFILES=n` before opening
multiple files.
* **`NEW` clears everything:** Variables, arrays, and the program. Use it
before loading a new program after a crash.
* **`REM` vs `'`:** Apostrophe works as REM and doesn't need a colon
separator: `10 X=X+1' comment` saves a byte vs `10 X=X+1:REM comment`
* **CALL / ARG / PUSH / POP:** Machine code interface. ARG loads E and C registers with a 16-bit value. PUSH/POP for the linkage stack.
* **EOF(n):** Returns -1 at end of file, 0 if more data. Same as MBASIC.
* **EOF and CP/M record padding:** CP/M pads files to 128-byte record
boundaries. `EOF(n)` may not trigger until a read actually fails on
the padding bytes. Use `ON ERROR GOTO` to catch `*IPE Error` at end
of file as a safety net:

``` basic
ON ERROR GOTO 500
...
500 RESUME 600
600 ON ERROR GOTO 0
601 CLOSE#1
```

* **`INPUT#` reads one line per call:** Each `INPUT#1,A,B,C` reads one
line and distributes comma-delimited fields to variables. Extra fields
on the line produce `?extra ignored`. Missing fields cause `?REDO from start` and re-read. It does NOT read across line boundaries.

- - -

## Verification Status (randomly "complete")

| Item | Status |
| ---- | ------ |
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
| Hard reset via Ctrl+C on power-on + code 56580 | **Confirmed** on hardware |
| INCHR low-power wait vs INKEY$ polling | **Confirmed** on hardware — battery drain noticeable with INKEY$ loop |
| OPCHR faster than PRINT CHR$() | From BASIC token architecture — not timed on hardware |
| Power-off POKE inhibit | **Confirmed** on hardware (stuck power button) |
| Power-off POKE recovery | **Confirmed** on hardware |
| DIM Error after crash / need NEW | **Confirmed** on hardware |
| Serial port settings / addresses | From manual + partial hardware testing |
| RS-232 voltage levels (not TTL) | From manual / ROM analysis — not scope-verified |



*Last updated: March 2026*
*Source: Husky Hunter Manual V09F 1984 + hardware testing*