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

