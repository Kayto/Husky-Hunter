# HBA_Format

Reference material and tools for the Husky Hunter BASIC tokenized file format.

---

## Background

The Husky Hunter stores BASIC programs on its CP/M disk in a **tokenized binary
format**.  When you use HCOM to upload a plain-ASCII `.BAS` source file from the
PC, the file lands on the Hunter's disk unchanged.  Programs can then be run in
two ways:

| Method | Requirement |
|--------|-------------|
| Enter `BAS`, then `LOAD "file.HBA"` | Works with plain ASCII |
| Run directly from DEMOS (CP/M shell) | Requires **tokenized binary** format |

DEMOS runs a program by loading its binary directly into the BASIC interpreter's
memory.  A plain-ASCII file does not match the expected memory layout so DEMOS
rejects it or produces garbage.

**The tokenized format** is created on-device when you `LOAD` then `SAVE` a file
inside BAS — the Hunter's own BASIC interpreter performs the ASCII→binary
conversion.  The files in `HSYNC/` were obtained this way: uploaded as ASCII via
HCOM, LOAD/SAVE'd on the Hunter, then received back to PC with HCOM.

Alternatively, `hba_tokenize.py` (or the GUI `HBA_Tokenizer.exe`) can perform
the ASCII→binary conversion on the PC, so you can upload a ready-to-run `.HBA`
binary directly without the manual LOAD/SAVE step on the Hunter.

Pre-built binaries for all programs in this repository are provided in the
[`HBA/`](../HBA/) folder at the repository root — ready to transfer straight to
the Hunter via HCOM.

---

## File Format

### Magic byte

All tokenized `.HBA` files start with `0xF1`.  Plain ASCII files start with the
ASCII digit of the first line number (e.g. `0x31` = `'1'`).

### Line records

After the magic byte, the file is a sequence of line records:

```
[length]  [line_lo]  [line_hi]  [tokenized content ...]  [0x0D]
```

| Field | Size | Description |
|-------|------|-------------|
| `length` | 1 byte | Total bytes in this record, including the length byte itself |
| `line_lo` | 1 byte | Line number, low byte (little-endian) |
| `line_hi` | 1 byte | Line number, high byte |
| content | variable | Tokenized BASIC statement(s), see token table |
| `0x0D` | 1 byte | Record terminator (CR) |

### End-of-program marker

After the last line record, a single byte `0x01` marks end-of-program (a record
of length 1, which contains only its own length field and nothing else).

### CP/M sector padding

The file is zero-padded to the next 128-byte boundary (CP/M sector size).  Any
bytes beyond the `0x01` EOF marker are undefined — the Hunter does not clear
them, so they may contain remnants of previously stored data.

### Encoding rules

- Keywords and operators are replaced by token bytes (see TOKEN_TABLE.md).
- Inter-token **spaces are not stored** — `PRINT "X"` tokenizes with no space
  between the PRINT token and the quote.
- **REM** is an exception: the text of the comment (including the leading space)
  is stored verbatim after the REM token, e.g. `REM Hello` → `8F 20 48 65 6C 6C 6F`.
- **String literals** (between `"..."`) are stored verbatim including the quotes.
- **Variable names**, **numbers**, and **line-number targets** in GOTO/GOSUB/THEN
  are stored as ASCII bytes.
- The compound-statement separator `:` is stored as ASCII `0x3A`.
- File handle `#1` etc. — `#` is ASCII `0x23`, digit follows as ASCII.
- `$`-functions (`CHR$(`, `LEFT$(`, etc.) absorb the open parenthesis into the
  token byte — **no `E0` is emitted** after the token.
- Plain functions (`INT(`, `SIN(`, `PEEK(`, etc.) follow their token with the
  open paren tokenized as `E0`.

---

## Tools

### HBA_Tokenizer.exe — GUI (recommended)

`HBA_Tokenizer.exe` is the easiest way to convert `.BAS` files on Windows.
No Python installation required — it is a self-contained Windows executable.
Drag-and-drop or browse for one or more `.BAS` files and click **Convert**;
each produces a `.HBA` binary alongside the source.

### hba_tokenize.py — command line

For scripting or automation, the command-line converter can be used directly:

```
python hba_tokenize.py INPUT.BAS [OUTPUT.HBA]
```

If `OUTPUT.HBA` is omitted, the output is written as `INPUT.HBA` alongside
the source.  Requires Python 3; no third-party packages needed.

### hba_convert_gui.py — GUI source

The Python source for the GUI.  Run directly with `python hba_convert_gui.py`
if you have Python installed; requires `hba_tokenize.py` as a sibling file.

### Coverage warning

> The token table was reverse-engineered from Hunter-native reference binaries.
> It covers most keywords that I have used to date, but Hunter BASIC has
> additional keywords not yet confirmed against hardware.  Those are either absent
> from the table or marked as **inferred** (value derived by sequence only).
> If a converted program behaves unexpectedly on the Hunter, check
> [`TOKEN_REFERENCE.md`](TOKEN_REFERENCE.md) for the current coverage and
> confirmation status of the keywords you are using.

---

## See Also

- `TOKEN_REFERENCE.md` — Token byte assignments for all Hunter BASIC keywords
- `HUNTER_BASIC_GOTCHAS.md` — Syntax differences from MBASIC/GW-BASIC
- `Dev/README.md` — Validation results, reverse-engineering notes, Hunter SAVE normalisations
