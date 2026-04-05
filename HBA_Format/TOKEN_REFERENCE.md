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
| `LET` | `80` |
| `LPRINT` | `89` — output to RS-232 |
| `CLEAR` | `90` — clears all variables |
| `PUSH` | `91` |
| `POKE` | `92` |
| `LOCATE` | `93` |
| `ERROR` | `94` — also sub-token in `ON ERROR` (`9F 94`) |
| `PRINT` | `95` |
| `INCHR` | `96` — read keypress; returns decimal ASCII value to numeric var |
| `OPCHR` | `97` — print raw character code(s) |
| `LINPUT` | `98` |
| `LINCHR` | `99` — read char from RS-232 |
| `LOPCHR` | `9A` — send char to RS-232 |
| `HELP` | `9B` |
| `POWER` | `9C` — `POWER n` (timeout interval); sub-tokens: OFF=`D9`, CONT=`A8` |
| `WINCHR` | `9D` — read char from optical wand |
| `BEEP` | `9E` |
| `ON` | `9F` |
| `ON ERROR` | `9F 94` |
| `SPC` | `A1` — used in `PRINT SPC(n)` |
| `TAB` | `A2` — used in `PRINT TAB(n)` |
| `LLIST` | `A7` — list program to RS-232 |
| `CONT` | `A8` — continue execution |
| `SYSTEM` | `AA` |
| `NEW` | `AB` † |
| `LLOAD` | `AC` — load program from RS-232 |
| `LIST` | `AD` † |
| `CRT` | `AE` — switch console to RS-232 |

† Not yet confirmed against hardware binary; value inferred from sequence.

### Multi-word statement sequences

| Source text | Hex | Notes |
|-------------|-----|-------|
| `POWER OFF` | `9C D9` | |
| `POWER CONT` | `9C A8` | disable power-off |
| `INPUT USING` | `8A D6` | `USING` sub-token = `D6` |
| `ON BREAK GOSUB` | `9F D8 84` | `BREAK` sub-token = `D8` |
| `ON COMMS GOSUB` | `9F DB 84` | `COMMS` sub-token = `DB` |

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
| `SWAP` | `FE 8A` |
| `STOP` | `FE 8C` |
| `TRON` | `FE 93` |
| `TROFF` | `FE 94` |
| `INKEY` | `FE 9E` — statement-style: `INKEY var` (non-blocking) |
| `KILL` | `FE 82` — delete file |
| `DEFSEG` | `FE 98` — define RAM page |
| `MAXFILES` | `FE 9D` |
| `OUT` | `FE 99` — output to port |
| `LTRON` | `FE 96` — trace to RS-232 |
| `FILES` | `FE 97` — list files |
| `WAND` | `FE A0` — optical wand decode |
| `WINPUT` | `FE 9C` — input string from wand |
| `COM` | `FE 8B` — communications; also sub-token in `ON COM(n)` |
| `NAME` | `FE 9F` — rename file (`NAME "old" AS "new"`) |
| `AS` | `FE A1` — sub-token in `FOR … AS` (OPEN) and `NAME … AS` |
| `KEY` | `FE 91` — bare KEY for `KEY(n)` context; `KEY OFF`=`FE 91 D9`, `KEY ON`=`FE 91 9F` |

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
| `EXP` | `DD` | |
| `RND` | `BE` | dummy arg required: `RND(0)` |
| `TAN` | `C7` | |
| `POS` | `B1` | |
| `VARPTR` | `C1` | |
| `COS` | `FE C8` | |
| `FIX` | `FE B6` | truncate toward zero (cf. INT which floors) |
| `INSTR` | `FE B0` | |
| `PEEK` | `FE CA` | |
| `ABS` | `FE CC` | |
| `FRE` | `FE CD` | |
| `SRCH` | `C0` | syntax: `SRCH(array_element, count)` |
| `LOC` | `B8` | |
| `INP` | `FE CB` | read from port |
| `POINT` | `FE D6` | returns pixel state |
| `ERR` | `FE B1` | error code after `ON ERROR` handler |
| `ERL` | `FE B2` | line number of last error |
| `POP` | `FE C9` | return value from machine-code stack |

### String functions — `$(` absorbed into token (no `E0` follows)

e.g. `CHR$(65)` → `D4 36 35 29`

| Function | Hex |
|----------|-----|
| `CHR$(` | `D4` |
| `STR$(` | `D2` |
| `MID$(` | `D0` |
| `LEFT$(` | `CE` |
| `RIGHT$(` | `CF` |
| `SPACE$(` | `CB` |
| `STRING$(` | `CC` |
| `JSR$(` | `DA` — fixed-field string from machine-code |

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
| 5.2.1  | `ABS`              | Function       | `FE CC`                 | |
| 5.2.2  | `ARG`              | Function       | —                       | Sets up argument for CALL |
| 5.2.3  | `ASC`              | Function       | `B7`                    | Returns decimal equivalent of string |
| 5.2.4  | `ATN`              | Function       | `C4`                    | Arc-tangent |
| 5.3.1  | `BEEP`             | Command        | `9E`                    | |
| 5.4.1  | `CALL`             | Statement      | —                       | Calls machine-code subroutine |
| 5.4.2  | `CHAR`             | Statement      | `FE 84`                 | Sets character size in graphics mode |
| 5.4.3  | `CHR$(`            | Function       | `D4`                    | Returns string equivalent of argument |
| 5.4.4  | `CIRCLE`           | Statement      | `FE 87`                 | Draws circle on LCD |
| 5.4.5  | `CLEAR`            | Command        | `90`                    | Clears all variables |
| 5.4.6  | `CLOSE`            | Statement      | `FE 9A`                 | Closes files |
| 5.4.7  | `CLS`              | Command        | `FE 83`                 | Clears the display screen |
| 5.4.8  | `COM`              | Command        | `FE 8B`                 | Activates/deactivates communications interrupt |
| 5.4.9  | `CONT`             | Command        | `A8`                    | Continues execution of program |
| 5.4.10 | `COS`              | Function       | `FE C8`                 | |
| 5.4.11 | `CRT`              | Command        | `AE`                    | Switches console to RS-232 port |
| 5.4.12 | `CUROFF` / `CURON` | Command        | `FE 81 D9` / `FE 81 9F` | |
| 5.5.1  | `DATA`             | Statement      | `87`                    | |
| 5.5.2  | `DATE$`            | Function       | `CA`                    | Current date string (assignable) |
| 5.5.3  | `DAY$`             | Function       | `C8`                    | Current day-of-week string |
| 5.5.4  | `DEFSEG`           | Command        | `FE 98`                 | Defines RAM page |
| 5.5.5  | `DELETE`           | Command        | —                       | Delete program lines |
| 5.5.6  | `DIM`              | Statement      | `8B`                    | Initialises arrays |
| 5.6.1  | `EDIT`             | Command        | —                       | Enters Basic editor |
| 5.6.2  | `END`              | Statement      | `8D`                    | Terminates execution |
| 5.6.3  | `EOF`              | I/O Function   | `B0`                    | Detects end of file |
| 5.6.4  | `ERR` / `ERL`      | Function       | `FE B1` / `FE B2`       | Returns error code / line number |
| 5.6.5  | `ERROR`            | Statement      | `94`                    | Simulates Basic error; also sub-token in `ON ERROR` |
| 5.6.6  | `EXP`              | Function       | `DD`                    | Returns e to the power of argument |
| 5.7.1  | `FILES`            | Command        | `FE 97`                 | Displays current files |
| 5.7.2  | `FIX`              | Function       | `FE B6`                 | Strips argument to integer (rounds toward zero) |
| 5.7.3  | `FOR`              | Statement      | `88`                    | Starts FOR…NEXT loop; also used in OPEN |
| 5.7.4  | `FRE`              | Function       | `FE CD`                 | Returns number of free bytes |
| 5.8.1  | `GOSUB`            | Statement      | `84`                    | |
| 5.8.2  | `GOTO`             | Statement      | `83`                    | |
| 5.9.1  | `HELP`             | Statement      | `9B`                    | Initialises HELP key text pointer |
| 5.10.1 | `IF`               | Statement      | `82`                    | |
| 5.10.2 | `IF…THEN…ELSE`     | Statement      | `82` / `A3` / `FE 90`   | |
| 5.10.3 | `INCHR`            | I/O Statement  | `96`                    | Returns single character from keyboard as decimal ASCII value |
| 5.10.4 | `INKEY`            | I/O Statement  | `FE 9E`                 | Returns keyboard status (numeric); statement-style: `INKEY var` |
| 5.10.5 | `INKEY$`           | I/O Statement  | `CD`                    | Returns single character if input pending |
| 5.10.6 | `INP`              | I/O Statement  | `FE CB`                 | Returns value at port address |
| 5.10.7 | `INPUT`            | Statement      | `8A`                    | Returns data input from keyboard |
| 5.10.8 | `INPUT USING`      | Statement      | `8A D6`                 | Validates data input; USING sub-token = `D6` |
| 5.10.9 | `INPUT#`           | I/O Statement  | `8A 23`                 | Input data from file |
| 5.10.10| `INSTR`            | Function       | `FE B0`                 | Returns position of second string in first |
| 5.10.11| `INT`              | Function       | `B6`                    | |
| 5.11.1 | `JSR$(`            | Function       | `DA`                    | Returns fixed-field string; `$(` absorbed into token |
| 5.12.1 | `KEY`              | Command        | `FE 91`                 | Initialises soft keys; `KEY OFF`=`FE 91 D9`, `KEY ON`=`FE 91 9F` |
| 5.12.2 | `KEY(n)`           | Command        | `FE 91`                 | Activates/deactivates soft keys |
| 5.12.3 | `KILL`             | Command        | `FE 82`                 | Deletes file |
| 5.13.1 | `LEFT$(`           | Function       | `CE`                    | |
| 5.13.2 | `LEN`              | Function       | `D1`                    | |
| 5.13.3 | `LET`              | Statement      | `80`                    | Assigns value of variable (usually implicit) |
| 5.13.4 | `LINCHR`           | I/O Statement  | `99`                    | Returns single character from RS-232 |
| 5.13.5 | `LINE`             | Statement      | `FE 80`                 | Draws straight line |
| 5.13.6 | `LINPUT`           | I/O Statement  | `98`                    | Returns entry from RS-232 |
| 5.13.7 | `LIST`             | Command        | `AD` †                  | Lists program at LCD |
| 5.13.8 | `LLIST`            | I/O Statement  | `A7`                    | Lists program at RS-232 |
| 5.13.9 | `LLOAD`            | Statement      | `AC`                    | Loads program from RS-232 |
| 5.13.10| `LN`               | Function       | `DE`                    | Natural logarithm |
| 5.13.11| `LOAD`             | Command        | —                       | Loads program from file — token not yet confirmed |
| 5.13.12| `LOC`              | I/O Function   | `B8`                    | Number of records read/written |
| 5.13.13| `LOCATE`           | Command        | `93`                    | Sets cursor position |
| 5.13.14| `LOG`              | Function       | `DF`                    | Logarithm **base 10** — note: reversed from MBASIC convention |
| 5.13.15| `LOPCHR`           | I/O Statement  | `9A`                    | Sends single character to RS-232 |
| 5.13.16| `LPRINT`           | I/O Statement  | `89`                    | Outputs to RS-232 |
| 5.13.17| `LTRON`            | I/O Statement  | `FE 96`                 | Sends trace output to RS-232 |
| 5.14.1 | `MAXFILES`         | I/O Statement  | `FE 9D`                 | Maximum number of files to be opened |
| 5.14.2 | `MID$(`            | Function       | `D0`                    | |
| 5.15.1 | `NAME`             | Command        | `FE 9F`                 | Re-names file; used with `AS` (`FE A1`) |
| 5.15.2 | `NEW`              | Command        | `AB` †                  | Initialises program space |
| 5.15.3 | `NEXT`             | Statement      | `81`                    | Concludes FOR…NEXT loop |
| 5.16.1 | `ON BREAK`         | I/O Statement  | `9F D8`                 | Vectors program on BREAK key; BREAK sub-token = `D8` |
| 5.16.2 | `ON COM`           | I/O Statement  | `9F FE 8B`              | Vectors program on communication |
| 5.16.3 | `ON COMMS`         | I/O Statement  | `9F DB`                 | Vectors program on COMMS failure; COMMS sub-token = `DB` |
| 5.16.4 | `ON ERROR`         | Statement      | `9F 94`                 | Vectors program on syntax error |
| 5.16.5 | `ON GOSUB`         | Statement      | `9F … 84`               | Conditional GOSUB; reuses ON=`9F`, GOSUB=`84` |
| 5.16.6 | `ON GOTO`          | Statement      | `9F … 83`               | Conditional GOTO; reuses ON=`9F`, GOTO=`83` |
| 5.16.7 | `ON KEY`           | I/O Statement  | `9F FE 91`              | Vectors program on soft keys |
| 5.16.8 | `ON POWER`         | I/O Statement  | `9F 9C`                 | Vectors program on POWER key |
| 5.16.9 | `ON POWER RESUME`  | I/O Statement  | `9F 9C 8C`              | Restarts program on power up |
| 5.16.10| `ON TIME$`         | Statement      | `9F C9`                 | Vectors program on system time |
| 5.16.11| `OPCHR`            | Statement      | `97`                    | Outputs 1 or more ASCII characters |
| 5.16.12| `OPEN`             | I/O Statement  | `FE 95`                 | Opens file for input/output |
| 5.16.13| `OUT`              | I/O Statement  | `FE 99`                 | Outputs to specified port |
| 5.17.1 | `PEEK`             | Function       | `FE CA`                 | Returns decimal byte value at memory location |
| 5.17.2 | `PI`               | Constant       | *not tokenized*         | Stored as literal ASCII "PI" at runtime |
| 5.17.3 | `POINT`            | Function       | `FE D6`                 | Returns condition of pixel |
| 5.17.4 | `POKE`             | Statement      | `92`                    | Sets memory location with decimal value |
| 5.17.5 | `POP`              | Statement      | `FE C9`                 | Returns value from machine code linkage/stack |
| 5.17.6 | `POS`              | Function       | `B1`                    | Returns cursor position |
| 5.17.7 | `POWER`            | Statement      | `9C`                    | Specifies auto time-off interval |
| 5.17.8 | `POWER CONT`       | Command        | `9C A8`                 | Disables power-off key and timeouts |
| 5.17.9 | `POWER OFF`        | Command        | `9C D9`                 | Switches Hunter off |
| 5.17.11| `PRINT`            | Statement      | `95`                    | Outputs to LCD |
| 5.17.13| `PRINT#`           | I/O Statement  | `95 23`                 | Output data to file |
| 5.17.14| `PSET` / `PRESET`  | Statement      | `FE 86`                 | Set/re-set pixel |
| 5.17.15| `PUSH`             | Statement      | `91`                    | Puts value onto machine code linkage stack |
| 5.19.1 | `READ`             | Statement      | `86`                    | Returns value from DATA statement |
| 5.19.2 | `REM`              | Statement      | `8F`                    | Comment; text stored verbatim after token |
| 5.19.3 | `RESTORE`          | Statement      | `8E`                    | Resets READ pointer |
| 5.19.4 | `RESUME`           | Statement      | `8C`                    | Restarts program at specified line |
| 5.19.5 | `RETURN`           | Statement      | `85`                    | Returns from subroutine |
| 5.19.6 | `RIGHT$(`          | Function       | `CF`                    | |
| 5.19.7 | `RND`              | Function       | `BE`                    | Produces random number; dummy arg required: `RND(0)` |
| 5.19.8 | `RUN`              | Command        | —                       | Starts program execution — token not yet confirmed |
| 5.20.1 | `SAVE`             | Command        | —                       | Writes program to file |
| 5.20.2 | `SCREEN`           | Command        | `FE 85`                 | Changes screen mode |
| 5.20.3 | `SGN`              | Function       | `C2`                    | Returns sign of argument |
| 5.20.4 | `SIN`              | Function       | `C3`                    | |
| 5.20.5 | `SOUND`            | Command        | `FE 89`                 | Generates specified tone |
| 5.20.6 | `SPACE$(`          | Function       | `CB`                    | Returns string of spaces; `$(` absorbed into token |
| 5.20.7 | `SPC`              | Function       | `A1`                    | Prints spaces in PRINT statement |
| 5.20.8 | `SQR`              | Function       | `B4`                    | |
| 5.20.9 | `SRCH`             | Function       | `C0`                    | Returns target string array position |
| 5.20.10| `STOP`             | Statement      | `FE 8C`                 | Terminates program execution |
| 5.20.11| `STR$(`            | Function       | `D2`                    | Returns string equivalent of numeric argument |
| 5.20.12| `STRING$(`         | Function       | `CC`                    | Returns string of characters; `$(` absorbed into token |
| 5.20.13| `SWAP`             | Statement      | `FE 8A`                 | Exchanges contents of two variables |
| 5.21.1 | `TAB`              | I/O Statement  | `A2`                    | Formats PRINT output |
| 5.21.2 | `TAN`              | Function       | `C7`                    | Returns tangent of argument |
| 5.21.3 | `TIME$`            | Function       | `C9`                    | Returns current time string |
| 5.21.4 | `TRON` / `TROFF`   | Command        | `FE 93` / `FE 94`       | Turns trace on/off |
| 5.22.1 | `USR`              | Function       | —                       | Calls machine-code subroutine (alternative to CALL) |
| 5.23.1 | `VAL`              | Function       | `D3`                    | Returns numeric value of string |
| 5.23.2 | `VARPTR`           | Function       | `C1`                    | Returns address of variable |
| 5.24.1 | `WAND`             | Command        | `FE A0`                 | Defines wand decode software |
| 5.24.2 | `WHILE` / `WEND`   | Statement      | `FE 8E` / `FE 8D`       | |
| 5.24.3 | `WINCHR`           | I/O Statement  | `9D`                    | Inputs single character from optical wand |
| 5.24.4 | `WINPUT`           | I/O Function   | `FE 9C`                 | Inputs string from optical wand |
| 5.24.5 | `WRITE#`           | I/O Function   | `FE 9B 23`              | Write data to file |

† Token value inferred from sequence, not yet confirmed against hardware binary.
