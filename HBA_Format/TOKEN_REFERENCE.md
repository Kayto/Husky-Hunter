# Husky Hunter BASIC — Token Reference

Reverse-engineered from Hunter-native tokenized `.HBA` binaries.
Hardware: Husky Hunter, DEMOS 2.2, V 9G06h ROM.

Work in Progress - all items subject to change!

---

## File Format

Each tokenized file begins with magic byte `F1`.  Line records follow:

```
[length] [line_lo] [line_hi] [tokenized content...] [0x0D]
```

`length` counts all bytes from itself to the end of the record (inclusive of `0x0D`).
Line number is little-endian 16-bit.  File ends with a record of `length=01` at line 0,
padded with `0x00` to the next 128-byte CP/M sector boundary.

Files without the `F1` magic byte are treated as plain ASCII source by DEMOS and
must be `LOAD`ed before they can run.

---

## Statements

| Keyword | Hex |
|---------|-----|
| `NEXT` | `81` |
| `IF` | `82` |
| `GOTO` | `83` |
| `GOSUB` | `84` |
| `RETURN` | `85` |
| `READ` | `86` |
| `DATA` | `87` |
| `FOR` | `88` — also used inside `OPEN … FOR …` |
| `INPUT` | `8A` |
| `DIM` | `8B` |
| `RESUME` | `8C` |
| `END` | `8D` |
| `RESTORE` | `8E` |
| `REM` | `8F` — comment text stored verbatim (including leading space) |
| `POKE` | `92` |
| `LOCATE` | `93` |
| `ON` | `9F` |
| `ON ERROR` | `9F 94` |
| `PRINT` | `95` |
| `OPCHR` | `97` — print raw character code(s) |
| `INCHR` | `96` — read keypress; returns decimal ASCII value to numeric var |
| `LINPUT` | `98` |
| `BEEP` | `9E` |
| `SYSTEM` | `AA` |
| `NEW` | `AB` * |
| `RUN` | `AC` * |
| `LIST` | `AD` * |
| `LOAD` | `AE` * |

\* Not yet confirmed against hardware binary; value inferred from sequence.

---

## Extended Statements (`FE` prefix)

| Keyword | Hex |
|---------|-----|
| `CLS` | `FE 83` |
| `LINE` | `FE 80` — graphics line |
| `CUROFF` | `FE 81 D9` |
| `CURON` | `FE 81 9F` |
| `CHAR` | `FE 84` |
| `SCREEN` | `FE 85` |
| `PSET` | `FE 86` |
| `CIRCLE` | `FE 87` |
| `SOUND` | `FE 89` |
| `WHILE` | `FE 8E` |
| `WEND` | `FE 8D` |
| `ELSE` | `FE 90` |
| `KEY OFF` | `FE 91 D9` |
| `KEY ON` | `FE 91 9F` |
| `OPEN` | `FE 95` |
| `CLOSE` | `FE 9A` |

### OPEN file-mode sequences (follow the filename string)

| Source text | Hex |
|-------------|-----|
| `FOR INPUT AS` | `88 8A FE A1` |
| `FOR OUTPUT AS` | `88 B3 FE A1` |
| `FOR APPEND AS` | `88 FE B5 FE A1` |

---

## Functions

Open paren `(` tokenizes separately as `E0`, so e.g. `INT(X)` → `B6 E0 58 29`.

| Function | Hex | Notes |
|----------|-----|-------|
| `INT` | `B6` | |
| `ASC` | `B7` | |
| `EOF` | `B0` | |
| `SIN` | `C3` | |
| `SGN` | `C2` | |
| `SQR` | `B4` | |
| `LOG` | `DF` | **base 10** on Hunter (opposite of MBASIC convention) |
| `LN` | `DE` | natural log |
| `ATN` | `C4` | |
| `LEN` | `D1` | |
| `VAL` | `D3` | |
| `COS` | `FE C8` | |
| `PEEK` | `FE CA` | |
| `ABS` | `FE CC` | |
| `FRE` | `FE CD` | |

### String functions — `$(` absorbed into token (no `E0` follows)

e.g. `CHR$(65)` → `D4 36 35 29`

| Function | Hex |
|----------|-----|
| `CHR$(` | `D4` |
| `STR$(` | `D2` |
| `MID$(` | `D0` |
| `LEFT$(` | `CE` |
| `RIGHT$(` | `CF` |

---

## Built-in Variables

| Name | Hex |
|------|-----|
| `INKEY$` | `CD` |
| `DAY$` | `C8` |
| `TIME$` | `C9` |
| `DATE$` | `CA` |

---

## Operators

### Relational

| Operator | Hex |
|----------|-----|
| `=` | `F5` |
| `<` | `F4` |
| `>` | `F6` |
| `<>` | `F1` |
| `<=` | `E4` |
| `>=` | `EC` |

### Arithmetic

| Operator | Hex | Notes |
|----------|-----|-------|
| `+` | `E3` | |
| `-` | `E5` | also used as range separator in `LINE` |
| `*` | `E2` | |
| `/` | `E7` | |
| `^` | `E1` | |
| `(` | `E0` | not used after string `$(` functions |
| `)` | `29` | ASCII literal |

### Keywords used as operators

| Keyword | Hex | Notes |
|---------|-----|-------|
| `AND` | `ED` | |
| `OR` | `EE` | |
| `NOT` | `F3` | |
| `THEN` | `A3` | |
| `TO` | `A4` | |
| `STEP` | `A5` | |
| `ELSE` | `FE 90` | |
| `MOD` | — | **not a Hunter BASIC keyword** — causes `*STX Error` |

---

## File I/O Keywords

| Keyword | Hex | Notes |
|---------|-----|-------|
| `INPUT#` | `8A 23` | no space — `8A` then ASCII `#` |
| `PRINT#` | `95 23` | |
| `WRITE#` | `FE 9B 23` | |

---

## ASCII Passthrough

The following are stored as literal bytes and never tokenized:

| Character | Hex |
|-----------|-----|
| `:` | `3A` — compound statement separator |
| `;` | `3B` — PRINT separator |
| `,` | `2C` — argument separator |
| `#` | `23` — file handle prefix |
| `"…"` | `22 … 22` — string literals stored verbatim |
| `0–9` | `30–39` — numeric literals stored as ASCII digits |
| `A–Z` | `41–5A` — variable names stored as ASCII |
| `$` | `24` — string variable suffix |

---

## Complete Official Keyword Index

All keywords listed in the Hunter BASIC manual index (V09F ROM, section 5).
Token bytes shown where identified; `—` indicates token not yet mapped.

| § | Keyword | Type | Token | Notes |
|---|---------|------|-------|-------|
| 5.2.1  | `ABS`              | Function       | `FE CC`                     | |
| 5.2.2  | `ARG`              | Function       | —                           | Sets up argument for CALL |
| 5.2.3  | `ASC`              | Function       | `B7`                        | Returns decimal equivalent of string |
| 5.2.4  | `ATN`              | Function       | `C4`                        | Arc-tangent |
| 5.3.1  | `BEEP`             | Command        | `9E`                        | |
| 5.4.1  | `CALL`             | Statement      | —                           | Calls machine-code subroutine |
| 5.4.2  | `CHAR`             | Statement      | `FE 84`                     | Sets character size in graphics mode |
| 5.4.3  | `CHR$(`            | Function       | `D4`                        | Returns string equivalent of argument |
| 5.4.4  | `CIRCLE`           | Statement      | `FE 87`                     | Draws circle on LCD |
| 5.4.5  | `CLEAR`            | Command        | —                           | Clears all variables |
| 5.4.6  | `CLOSE`            | Statement      | `FE 9A`                     | Closes files |
| 5.4.7  | `CLS`              | Command        | `FE 83`                     | Clears the display screen |
| 5.4.8  | `COM`              | Command        | —                           | Activates/deactivates communications interrupt |
| 5.4.9  | `CONT`             | Command        | —                           | Continues execution of program |
| 5.4.10 | `COS`              | Function       | `FE C8`                     | |
| 5.4.11 | `CRT`              | Command        | —                           | Switches console to RS-232 port |
| 5.4.12 | `CUROFF` / `CURON` | Command        | `FE 81 D9` / `FE 81 9F`     | |
| 5.5.1  | `DATA`             | Statement      | `87`                        | |
| 5.5.2  | `DATE$`            | Function       | `CA`                        | Current date string (assignable) |
| 5.5.3  | `DAY$`             | Function       | `C8`                        | Current day-of-week string |
| 5.5.4  | `DEFSEG`           | Command        | —                           | Defines RAM page |
| 5.5.5  | `DELETE`           | Command        | —                           | Delete program lines |
| 5.5.6  | `DIM`              | Statement      | `8B`                        | Initialises arrays |
| 5.6.1  | `EDIT`             | Command        | —                           | Enters Basic editor |
| 5.6.2  | `END`              | Statement      | `8D`                        | Terminates execution |
| 5.6.3  | `EOF`              | I/O Function   | `B0`                        | Detects end of file |
| 5.6.4  | `ERR` / `ERL`      | Function       | —                           | Returns error code / line number |
| 5.6.5  | `ERROR`            | Statement      | —                           | Simulates Basic error |
| 5.6.6  | `EXP`              | Function       | —                           | Returns e to the power of argument |
| 5.7.1  | `FILES`            | Command        | —                           | Displays current files |
| 5.7.2  | `FIX`              | Function       | —                           | Strips argument to integer |
| 5.7.3  | `FOR`              | Statement      | `88`                        | Starts FOR…NEXT loop; also used in OPEN |
| 5.7.4  | `FRE`              | Function       | `FE CD`                     | Returns number of free bytes |
| 5.8.1  | `GOSUB`            | Statement      | `84`                        | |
| 5.8.2  | `GOTO`             | Statement      | `83`                        | |
| 5.9.1  | `HELP`             | Statement      | —                           | Initialises HELP key text pointer |
| 5.10.1 | `IF`               | Statement      | `82`                        | |
| 5.10.2 | `IF…THEN…ELSE`     | Statement      | `82` / `A3` / `FE 90`       | |
| 5.10.3 | `INCHR`            | I/O Statement  | `96`                        | Returns single character from keyboard as decimal ASCII value |
| 5.10.4 | `INKEY`            | I/O Statement  | —                           | Returns keyboard status (numeric) |
| 5.10.5 | `INKEY$`           | I/O Statement  | `CD`                        | Returns single character if input pending |
| 5.10.6 | `INP`              | I/O Statement  | —                           | Returns value at port address |
| 5.10.7 | `INPUT`            | Statement      | `8A`                        | Returns data input from keyboard |
| 5.10.8 | `INPUT USING`      | Statement      | —                           | Validates data input from keyboard |
| 5.10.9 | `INPUT#`           | I/O Statement  | `8A 23`                     | Input data from file |
| 5.10.10| `INSTR`            | Function       | —                           | Returns position of second string in first |
| 5.10.11| `INT`              | Function       | `B6`                        | |
| 5.11.1 | `JSR$`             | Function       | —                           | Returns fixed-field string |
| 5.12.1 | `KEY`              | Command        | —                           | Initialises soft keys |
| 5.12.2 | `KEY(n)`           | Command        | —                           | Activates/deactivates soft keys |
| 5.12.3 | `KILL`             | Command        | —                           | Deletes file |
| 5.13.1 | `LEFT$(`           | Function       | `CE`                        | |
| 5.13.2 | `LEN`              | Function       | `D1`                        | |
| 5.13.3 | `LET`              | Statement      | —                           | Assigns value of variable (usually implicit) |
| 5.13.4 | `LINCHR`           | I/O Statement  | —                           | Returns single character from RS-232 |
| 5.13.5 | `LINE`             | Statement      | `FE 80`                     | Draws straight line |
| 5.13.6 | `LINPUT`           | I/O Statement  | `98`                        | Returns entry from RS-232 |
| 5.13.7 | `LIST`             | Command        | `AD` †                      | Lists program at LCD |
| 5.13.8 | `LLIST`            | I/O Statement  | —                           | Lists program at RS-232 |
| 5.13.9 | `LLOAD`            | Statement      | —                           | Loads program from RS-232 |
| 5.13.10| `LN`               | Function       | `DE`                        | Natural logarithm |
| 5.13.11| `LOAD`             | Command        | `AE` †                      | Loads program from file |
| 5.13.12| `LOC`              | I/O Function   | —                           | Number of records read/written |
| 5.13.13| `LOCATE`           | Command        | `93`                        | Sets cursor position |
| 5.13.14| `LOG`              | Function       | `DF`                        | Logarithm **base 10** — note: reversed from MBASIC convention |
| 5.13.15| `LOPCHR`           | I/O Statement  | —                           | Sends single character to RS-232 |
| 5.13.16| `LPRINT`           | I/O Statement  | —                           | Outputs to RS-232 |
| 5.13.17| `LTRON`            | I/O Statement  | —                           | Sends trace output to RS-232 |
| 5.14.1 | `MAXFILES`         | I/O Statement  | —                           | Maximum number of files to be opened |
| 5.14.2 | `MID$(`            | Function       | `D0`                        | |
| 5.15.1 | `NAME`             | Command        | —                           | Re-names file |
| 5.15.2 | `NEW`              | Command        | `AB` †                      | Initialises program space |
| 5.15.3 | `NEXT`             | Statement      | `81`                        | Concludes FOR…NEXT loop |
| 5.16.1 | `ON BREAK`         | I/O Statement  | —                           | Vectors program on BREAK key |
| 5.16.2 | `ON COM`           | I/O Statement  | —                           | Vectors program on communication |
| 5.16.3 | `ON COMMS`         | I/O Statement  | —                           | Vectors program on COMMS failure |
| 5.16.4 | `ON ERROR`         | Statement      | `9F 94`                     | Vectors program on syntax error |
| 5.16.5 | `ON GOSUB`         | Statement      | —                           | Conditional branch to subroutine |
| 5.16.6 | `ON GOTO`          | Statement      | —                           | Conditional branch |
| 5.16.7 | `ON KEY`           | I/O Statement  | —                           | Vectors program on soft keys |
| 5.16.8 | `ON POWER`         | I/O Statement  | —                           | Vectors program on POWER key |
| 5.16.9 | `ON POWER RESUME`  | I/O Statement  | —                           | Restarts program on power up |
| 5.16.10| `ON TIME$`         | Statement      | —                           | Vectors program on system time |
| 5.16.11| `OPCHR`            | Statement      | `97`                        | Outputs 1 or more ASCII characters |
| 5.16.12| `OPEN`             | I/O Statement  | `FE 95`                     | Opens file for input/output |
| 5.16.13| `OUT`              | I/O Statement  | —                           | Outputs to specified port |
| 5.17.1 | `PEEK`             | Function       | `FE CA`                     | Returns decimal byte value at memory location |
| 5.17.2 | `PI`               | Constant       | —                           | Value of PI = 3.14159 |
| 5.17.3 | `POINT`            | Function       | —                           | Returns condition of pixel |
| 5.17.4 | `POKE`             | Statement      | `92`                        | Sets memory location with decimal value |
| 5.17.5 | `POP`              | Statement      | —                           | Returns value from machine code linkage/stack |
| 5.17.6 | `POS`              | Function       | —                           | Returns cursor position |
| 5.17.7 | `POWER`            | Statement      | —                           | Specifies auto time-off interval |
| 5.17.8 | `POWER CONT`       | Command        | —                           | Disables power-off key and timeouts |
| 5.17.9 | `POWER OFF`        | Command        | —                           | Switches Hunter off |
| 5.17.11| `PRINT`            | Statement      | `95`                        | Outputs to LCD |
| 5.17.13| `PRINT#`           | I/O Statement  | `95 23`                     | Output data to file |
| 5.17.14| `PSET` / `PRESET`  | Statement      | `FE 86`                     | Set/re-set pixel |
| 5.17.15| `PUSH`             | Statement      | —                           | Puts value onto machine code linkage stack |
| 5.19.1 | `READ`             | Statement      | `86`                        | Returns value from DATA statement |
| 5.19.2 | `REM`              | Statement      | `8F`                        | Comment; text stored verbatim after token |
| 5.19.3 | `RESTORE`          | Statement      | `8E`                        | Resets READ pointer |
| 5.19.4 | `RESUME`           | Statement      | `8C`                        | Restarts program at specified line |
| 5.19.5 | `RETURN`           | Statement      | `85`                        | Returns from subroutine |
| 5.19.6 | `RIGHT$(`          | Function       | `CF`                        | |
| 5.19.7 | `RND`              | Function       | —                           | Produces random number |
| 5.19.8 | `RUN`              | Command        | `AC` †                      | Starts program execution |
| 5.20.1 | `SAVE`             | Command        | —                           | Writes program to file |
| 5.20.2 | `SCREEN`           | Command        | `FE 85`                     | Changes screen mode |
| 5.20.3 | `SGN`              | Function       | `C2`                        | Returns sign of argument |
| 5.20.4 | `SIN`              | Function       | `C3`                        | |
| 5.20.5 | `SOUND`            | Command        | `FE 89`                     | Generates specified tone |
| 5.20.6 | `SPACE$`           | Function       | —                           | Returns string of spaces |
| 5.20.7 | `SPC`              | Function       | —                           | Prints spaces in PRINT statement |
| 5.20.8 | `SQR`              | Function       | `B4`                        | |
| 5.20.9 | `SRCH`             | Function       | —                           | Returns target string array position |
| 5.20.10| `STOP`             | Statement      | —                           | Terminates program execution |
| 5.20.11| `STR$(`            | Function       | `D2`                        | Returns string equivalent of numeric argument |
| 5.20.12| `STRINGS`          | Function       | —                           | Returns string of characters |
| 5.20.13| `SWAP`             | Statement      | —                           | Exchanges contents of two variables |
| 5.21.1 | `TAB`              | I/O Statement  | —                           | Formats PRINT output |
| 5.21.2 | `TAN`              | Function       | —                           | Returns tangent of argument |
| 5.21.3 | `TIME$`            | Function       | `C9`                        | Returns current time string |
| 5.21.4 | `TRON` / `TROFF`   | Command        | —                           | Turns trace on/off |
| 5.23.1 | `VAL`              | Function       | `D3`                        | Returns numeric value of string |
| 5.23.2 | `VARPTR`           | Function       | —                           | Returns address of variable |
| 5.24.1 | `WAND`             | Command        | —                           | Defines wand decode software |
| 5.24.2 | `WHILE` / `WEND`   | Statement      | `FE 8E` / `FE 8D`           | |
| 5.24.3 | `WINCHR`           | I/O Statement  | —                           | Inputs single character from optical wand |
| 5.24.4 | `WINPUT`           | I/O Function   | —                           | Inputs string from optical wand |
| 5.24.5 | `WRITE#`           | I/O Function   | `FE 9B 23`                  | Write data to file |

† Token value inferred from sequence, not yet confirmed against hardware binary.
