#!/usr/bin/env python3
"""
hba_tokenize.py  —  Convert ASCII Husky Hunter BASIC (.BAS) to tokenized .HBA binary
By Kayto, April 2026
Licensed under the MIT License. See LICENSE file for details.

The Hunter stores BASIC programs as a tokenized binary on CP/M disk.
Files uploaded as plain ASCII via HCOM work via LOAD/SAVE on the Hunter,
but can only be run from DEMOS (the CP/M shell) if they are in tokenized
binary format (identified by the 0xF1 magic byte at offset 0).

This script converts a plain-ASCII .BAS source file to the tokenized
binary format that DEMOS can run directly, removing the need to manually
LOAD then SAVE on the Hunter after each upload.

Token table reverse-engineered from Hunter-native .HBA files (April 2026).
Reference hardware: Husky Hunter, DEMOS 2.2, V09F ROM.

Usage:
    python hba_tokenize.py INPUT.BAS [OUTPUT.HBA]

    If OUTPUT is omitted, writes INPUT.HBA alongside the input.

Format of each line record in the binary:
    [length]  [line_lo] [line_hi]  [tokenized content...]  [0x0D]
    ^-- length includes all bytes from this field to end of record (incl. 0x0D)
    ^-- line number is little-endian 16-bit

File structure:
    0xF1                   magic byte
    <line records...>      variable length
    0x01 0x00              end-of-program marker (length=1, line=0)
    0x00 * padding         to next 128-byte CP/M sector boundary
"""

import sys
import os
import re

# ---------------------------------------------------------------------------
# Token table — longest match wins (sorted longest-first at build time)
# Format: keyword string -> token byte(s)
#
# Rules observed in reference files:
#   - Keywords/statements tokenized to 1 or 3 bytes (0xFE prefix for extended)
#   - Operators tokenized to 1 byte
#   - Variables, numbers, strings remain as ASCII
#   - The ':' compound-statement separator stays as ASCII 0x3A
#   - '#' for file handles stays as ASCII 0x23
#   - String literals (between quotes) are NOT tokenized
# ---------------------------------------------------------------------------

TOKENS = {
    # --- Statements (single byte) ---
    "REM":      b"\x8F",
    "IF":       b"\x82",
    "GOTO":     b"\x83",
    "GOSUB":    b"\x84",      # confirmed from TTEST L60
    "RETURN":   b"\x85",      # confirmed from TTEST L9010
    "READ":     b"\x86",
    "DATA":     b"\x87",
    "FOR":      b"\x88",
    "INPUT":    b"\x8A",
    "DIM":      b"\x8B",
    "RESUME":   b"\x8C",     # confirmed from TERRAIN L9398
    "END":      b"\x8D",
    "RESTORE":  b"\x8E",
    "BEEP":     b"\x9E",     # confirmed from DEMO1 L1013
    "POKE":     b"\x92",
    "LOCATE":   b"\x93",
    "ON":       b"\x9F",     # confirmed from TERRAIN L310
    "PRINT":    b"\x95",
    "OPCHR":    b"\x97",     # confirmed from TTEST L210
    "INCHR":    b"\x96",     # confirmed from INCH.HBA L20/L40
    "LINPUT":   b"\x98",
    "NEXT":     b"\x81",
    "ON ERROR": b"\x9F\x94", # ON ERROR seen as 9F 94 in reference
    "SYSTEM":   b"\xAA",
    "NEW":      b"\xAB",     # inferred (still unconfirmed)
    "LLOAD":    b"\xAC",     # confirmed from MISC1.HBA L9280 (was inferred as RUN)
    "LIST":     b"\xAD",     # inferred (still unconfirmed)
    "CRT":      b"\xAE",     # confirmed from MISC1.HBA L9290 (was inferred as LOAD)
    "SWAP":     b"\xFE\x8A",  # confirmed from FUNC.HBA L230
    "STOP":     b"\xFE\x8C",  # confirmed from FUNC.HBA L320
    "TRON":     b"\xFE\x93",  # confirmed from FUNC.HBA L290
    "TROFF":    b"\xFE\x94",  # confirmed from FUNC.HBA L300
    "TAB":      b"\xA2",     # confirmed from FUNC.HBA L250
    "SPC":      b"\xA1",     # confirmed from FUNC.HBA L270

    # --- Extended statements (FE prefix) ---
    "LINE":     b"\xFE\x80",
    "CUROFF":   b"\xFE\x81\xD9",
    "CURON":    b"\xFE\x81\x9F",
    "CHAR":     b"\xFE\x84",
    "SCREEN":   b"\xFE\x85",
    "PSET":     b"\xFE\x86",
    "KEY OFF":  b"\xFE\x91\xD9",
    "KEY ON":   b"\xFE\x91\x9F",
    "WHILE":    b"\xFE\x8E",  # confirmed from TTEST L20
    "WEND":     b"\xFE\x8D",  # confirmed from TTEST L40
    "OPEN":     b"\xFE\x95",
    "CLOSE":    b"\xFE\x9A",
    "CIRCLE":   b"\xFE\x87",  # confirmed from DEMO1
    "CLS":      b"\xFE\x83",  # confirmed from DEMO1
    "SOUND":    b"\xFE\x89",  # confirmed from DEMO1

    # --- Functions ---
    # Non-$ functions: keyword does NOT include '(' — that open paren will then
    # be tokenized as E0 by the operator rule, giving e.g. INT( -> B6 E0.
    # $-functions: keyword INCLUDES '$(' to absorb the open paren (no E0 after).
    "INT":      b"\xB6",
    "ASC":      b"\xB7",     # confirmed from MORSE L132
    "SIN":      b"\xC3",
    "SGN":      b"\xC2",     # confirmed from TERRAIN L9010
    "FIX":      b"\xFE\xB6",  # confirmed from FUNC.HBA L30
    "INSTR":    b"\xFE\xB0",  # confirmed from FUNC.HBA L160
    "COS":      b"\xFE\xC8",
    "ABS":      b"\xFE\xCC",
    "FRE":      b"\xFE\xCD",
    "PEEK":     b"\xFE\xCA",
    "EOF":      b"\xB0",
    "SQR":      b"\xB4",     # confirmed from TERRAIN L9308
    "POS":      b"\xB1",     # confirmed from FUNC.HBA L110
    "RND":      b"\xBE",     # confirmed from FUNC.HBA L50
    "LOG":      b"\xDF",     # confirmed from TERRAIN L136 — log base 10 on Hunter
    "EXP":      b"\xDD",     # confirmed from FUNC.HBA L10
    "LN":       b"\xDE",     # confirmed from TTEST L80 — natural log on Hunter
    "ATN":      b"\xC4",     # confirmed from TTEST L90
    "TAN":      b"\xC7",     # confirmed from FUNC.HBA L70
    "VARPTR":   b"\xC1",     # confirmed from FUNC.HBA L130
    "ARG":      b"\xBC",     # confirmed from BDOSFN2.HBA L170
    "CALL":     b"\xBD",     # confirmed from BDOSFN2.HBA L180
    "LEN":      b"\xD1",     # confirmed from MORSE L122
    "VAL":      b"\xD3",     # confirmed from TTEST L120
    # $-functions absorb the open paren (no E0 after token)
    # Confirmed from SYSINFO reference: STR$( -> D2, SYSINFO/Y2KFIX: LEFT$( -> CE
    "CHR$(":    b"\xD4",
    "STR$(":    b"\xD2",
    "MID$(":    b"\xD0",     # confirmed from MORSE L124
    "LEFT$(":   b"\xCE",
    "RIGHT$(":  b"\xCF",     # confirmed from TTEST L150
    "SPACE$(": b"\xCB",     # confirmed from FUNC.HBA L180
    "STRING$(": b"\xCC",    # confirmed from FUNC.HBA L200

    # --- Variables / built-ins that are tokenized ---
    "INKEY$":   b"\xCD",
    "DATE$":    b"\xCA",
    "TIME$":    b"\xC9",
    "DAY$":     b"\xC8",

    # --- Operators ---
    "AND":      b"\xED",
    "OR":       b"\xEE",
    "NOT":      b"\xF3",         # confirmed from TTEST L170
    # MOD likely not a Hunter BASIC keyword — caused STX Error in testing
    "THEN":     b"\xA3",
    "TO":       b"\xA4",
    "STEP":     b"\xA5",
    "ELSE":     b"\xFE\x90",

    # --- Arithmetic/comparison operators ---
    "<>":       b"\xF1",
    "<=":       b"\xE4",         # confirmed from TERRAIN L1195
    ">=":       b"\xEC",         # confirmed from TERRAIN L1195
    ">":        b"\xF6",
    "<":        b"\xF4",
    "=":        b"\xF5",
    "(":        b"\xE0",
    ")":        b"\x29",         # ASCII literal — kept as-is
    "+":        b"\xE3",
    "-":        b"\xE5",         # E5 used for -(range) in LINE token context; also unary
    "*":        b"\xE2",
    "/":        b"\xE7",
    "^":        b"\xE1",         # confirmed from TTEST L190

    # OPEN keywords (appear after OPEN "file")
    "FOR INPUT AS":  b"\x88\x8A\xFE\xA1",   # confirmed from TERRAIN L525 — INPUT=8A same token
    "FOR OUTPUT AS": b"\x88\xB3\xFE\xA1",   # confirmed from TTEST L250
    "FOR APPEND AS": b"\x88\xFE\xB5\xFE\xA1",  # confirmed from TTEST L300; APPEND=FE B5
    "INPUT USING": b"\x8A\xD6",   # confirmed from MISC1.HBA L9250
    "INPUT#":   b"\x8A\x23",    # INPUT# (no space) — 8A then #
    "WRITE#":   b"\xFE\x9B\x23",  # confirmed from TTEST L260; WRITE=FE 9B
    "PRINT#":   b"\x95\x23",    # confirmed from TTEST L270

    # --- Confirmed from MISC1.HBA (April 2026) ---

    # Statements (single byte)
    "LET":      b"\x80",     # confirmed from MISC1.HBA L40
    "LPRINT":   b"\x89",     # confirmed from MISC1.HBA L9030 (fills gap at 89)
    "CLEAR":    b"\x90",     # confirmed from MISC1.HBA L9320
    "PUSH":     b"\x91",     # confirmed from MISC1.HBA L9180
    "ERROR":    b"\x94",     # confirmed from MISC1.HBA L270; also sub-token in ON ERROR
    "LINCHR":   b"\x99",     # confirmed from MISC1.HBA L9050
    "LOPCHR":   b"\x9A",     # confirmed from MISC1.HBA L9060
    "HELP":     b"\x9B",     # confirmed from MISC1.HBA L9080
    "WINCHR":   b"\x9D",     # confirmed from MISC1.HBA L9220
    "LLIST":    b"\xA7",     # confirmed from MISC1.HBA L9040
    "CONT":     b"\xA8",     # confirmed from MISC1.HBA L9310
    "BREAK":    b"\xD8",     # sub-token after ON; confirmed from MISC1.HBA L9090
    "COMMS":    b"\xDB",     # sub-token after ON; confirmed from MISC1.HBA L9150

    # Multi-word statements (must sort before component words — handled by length sort)
    "POWER OFF":  b"\x9C\xD9",   # confirmed from MISC1.HBA L9020
    "POWER CONT": b"\x9C\xA8",   # confirmed from MISC1.HBA L9170

    # Statements
    "INKEY":    b"\xFE\x9E",  # confirmed from MISC1.HBA L60; statement-style: INKEY var
    "POWER":    b"\x9C",     # confirmed from MISC1.HBA L9160

    # Extended statements (FE prefix)
    "KILL":     b"\xFE\x82", # confirmed from MISC1.HBA L9010
    "DEFSEG":   b"\xFE\x98", # confirmed from MISC1.HBA L140
    "MAXFILES": b"\xFE\x9D", # confirmed from MISC1.HBA L160
    "OUT":      b"\xFE\x99", # confirmed from MISC1.HBA L100
    "LTRON":    b"\xFE\x96", # confirmed from MISC1.HBA L9070
    "FILES":    b"\xFE\x97", # confirmed from MISC1.HBA L9300
    "WAND":     b"\xFE\xA0", # confirmed from MISC1.HBA L9240
    "WINPUT":   b"\xFE\x9C", # confirmed from MISC1.HBA L9230
    "COM":      b"\xFE\x8B", # confirmed from MISC1.HBA L9210 (also ON COM sub-token)
    "NAME":     b"\xFE\x9F", # confirmed from MISC1.HBA L9200
    "AS":       b"\xFE\xA1", # confirmed; sub-token in FOR...AS and NAME...AS

    # Functions (open paren follows as E0)
    "INP":      b"\xFE\xCB", # confirmed from MISC1.HBA L80
    "POINT":    b"\xFE\xD6", # confirmed from MISC1.HBA L120
    "SRCH":     b"\xC0",     # confirmed from MISC1.HBA L240
    "ERR":      b"\xFE\xB1", # confirmed from MISC1.HBA L280
    "ERL":      b"\xFE\xB2", # confirmed from MISC1.HBA L280
    "LOC":      b"\xB8",     # confirmed from MISC1.HBA L9270
    "POP":      b"\xFE\xC9", # confirmed from MISC1.HBA L9190

    # $-functions (absorb open paren; no E0 follows)
    "JSR$(": b"\xDA",        # confirmed from MISC1.HBA L9260

    # KEY bare token for KEY(n) context; KEY OFF / KEY ON are longer → match first
    "KEY":      b"\xFE\x91", # confirmed; KEY(n) for ON KEY(n) interrupt context
}

# Keywords that must be followed by a word boundary (space, '(', digit, etc.)
# — these are pure alpha keywords, not operator symbols
_WORD_BOUNDARY_REQUIRED = {kw for kw in TOKENS if kw[-1:].isalpha() or kw.endswith('$')}

# Build sorted keyword list (longest first for greedy matching)
# Separate into "statement-start" (only valid at start of statement) and
# "anywhere" tokens.  For now we apply all greedily outside string literals.
_SORTED_TOKENS = sorted(TOKENS.keys(), key=len, reverse=True)


def _is_word_char(ch):
    return ch.isalnum() or ch in ('$', '_', '#')


def tokenize_line_content(source_stmt):
    """
    Tokenize the content portion of one BASIC statement (everything after
    the line number).  String literals are passed through verbatim.
    Compound statements separated by ':' are each tokenized.
    Returns bytes (without the leading line-number or trailing 0x0D).

    Key rules observed from Hunter reference files:
      - Spaces between tokens are NOT stored (stripped)
      - REM text IS stored verbatim including leading space: 8F 20 <text>
      - String literals are stored verbatim including quotes
      - ':' compound separator is stored as ASCII 0x3A
    """
    result = bytearray()
    i = 0
    n = len(source_stmt)

    while i < n:
        ch = source_stmt[i]

        if ch == '"':
            # String literal — copy verbatim including quotes
            j = i + 1
            while j < n and source_stmt[j] != '"':
                j += 1
            literal = source_stmt[i:j+1]
            result.extend(literal.encode('ascii', errors='replace'))
            i = j + 1

        elif ch == "'":
            # Single-quote REM shorthand
            result.append(0x8F)
            rest = source_stmt[i+1:]
            result.extend(rest.encode('ascii', errors='replace'))
            break

        elif ch == ':':
            # Compound statement separator — emit as-is, then continue
            result.append(0x3A)
            i += 1

        elif ch == ' ':
            # Inter-token space — discard (tokenizer strips spaces)
            i += 1

        else:
            # Try to match a keyword at current position (greedy, longest first)
            upper = source_stmt.upper()
            matched = False
            for kw in _SORTED_TOKENS:
                kw_len = len(kw)
                end = i + kw_len
                if upper[i:end] == kw:
                    tok_bytes = TOKENS[kw]
                    result.extend(tok_bytes)
                    i = end

                    # Special case: REM — rest of compound segment is raw text
                    # REM stores one space then the comment verbatim.
                    if kw == "REM":
                        # Find end of this compound segment (next ':' that is
                        # not inside a string, or end of line)
                        # For REM there can't be a meaningful ':' after it,
                        # so just consume everything remaining.
                        rest = source_stmt[i:]
                        result.extend(rest.encode('ascii', errors='replace'))
                        i = n
                    matched = True
                    break

            if not matched:
                result.append(ord(source_stmt[i]))
                i += 1

    return bytes(result)
    return bytes(result)


def build_line_record(line_num, content_bytes):
    """
    Build a single line record:
        [length][line_lo][line_hi][content...][0x0D]
    length = total bytes in record including length byte itself.
    """
    # content + 0x0D + 3 header bytes (length, lo, hi)
    total = 1 + 2 + len(content_bytes) + 1   # length + linenum + content + CR
    if total > 255:
        raise ValueError(f"Line {line_num} too long after tokenization ({total} bytes)")
    record = bytearray()
    record.append(total)
    record.append(line_num & 0xFF)
    record.append((line_num >> 8) & 0xFF)
    record.extend(content_bytes)
    record.append(0x0D)
    return bytes(record)


def tokenize_file(src_text):
    """
    Convert full ASCII BASIC source text to tokenized binary.
    Returns bytes ready to write to disk.
    """
    output = bytearray()
    output.append(0xF1)   # magic

    for raw_line in src_text.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        # Split line number from content
        m = re.match(r'^(\d+)\s*(.*)', raw_line)
        if not m:
            continue
        line_num = int(m.group(1))
        stmt = m.group(2)
        content = tokenize_line_content(stmt)
        output.extend(build_line_record(line_num, content))

    # End-of-program marker observed in reference files:
    # After the last line record, the Hunter writes 0x01 (a record of length 1,
    # meaning only the length byte itself with no line number or content).
    # The remainder of the 128-byte sector is zeroed.
    output.append(0x01)

    # Pad with 0x00 to the next 128-byte CP/M sector boundary
    sector = 128
    remainder = len(output) % sector
    if remainder:
        output.extend(b"\x00" * (sector - remainder))

    return bytes(output)


def main():
    if len(sys.argv) < 2:
        print("Usage: hba_tokenize.py INPUT.HBA [OUTPUT.HBA]")
        sys.exit(1)

    in_path = sys.argv[1]
    if len(sys.argv) >= 3:
        out_path = sys.argv[2]
    else:
        base, ext = os.path.splitext(in_path)
        out_path = base + "_tok" + ext

    try:
        src_text = open(in_path, "r", encoding="ascii", errors="replace").read()
    except FileNotFoundError:
        print(f"ERROR: File not found: {in_path}")
        sys.exit(1)

    binary = tokenize_file(src_text)

    with open(out_path, "wb") as f:
        f.write(binary)

    # Report
    line_count = sum(1 for l in src_text.splitlines() if re.match(r'^\d+', l.strip()))
    print(f"Tokenized {line_count} lines  ->  {len(binary)} bytes  ->  {out_path}")


if __name__ == "__main__":
    main()
