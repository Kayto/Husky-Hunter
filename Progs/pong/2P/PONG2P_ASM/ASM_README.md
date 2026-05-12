# PONG2P_ASM — Assembly Reference Files

Human vs AI pong with delta paddle rendering and conditional scoring.
Z80 machine code loaded into Husky Hunter BASIC via `DIM`/`VARPTR` string array.

## Files

| File | Description |
|---|---|
| [PONG2P.asm](PONG2P.asm) | Full Z80 source (Intel-style mnemonics, H-suffix hex) |
| [PONG2P.lst](PONG2P.lst) | sjasmplus hex listing |
| [PONG2P.dlst](PONG2P.dlst) | Decorated listing with bytes in decimal (matches BASIC POKE values) |
| [POKE_LIST.txt](POKE_LIST.txt) | BASIC DATA lines 900–961 ready to type or paste |
| [sprite_data.txt](sprite_data.txt) | Ball sprite bytes and initial parameter block values |

Regenerate `.lst` / `.dlst` after editing the source:

```
sjasmplus --lst=PONG2P.lst PONG2P.asm
python ../../../Dev/asm_tools/lst_to_dlst.py PONG2P.lst PONG2P.dlst
```

---

## Program Summary

| Property | Value |
|---|---|
| Binary size | 906 bytes |
| BASIC loader | `DIM MC$(452,1)` / `AD=VARPTR(MC$)-1` / `ORG 0000H` |
| DATA lines | 900–960 (MC bytes), 961 (patch table) |
| Patch offsets | 51 (line 961) |
| PARAM_BASE | `F605H` = 62981 |
| Param block size | 18 bytes |

---

## Parameter Block (F605H, 18 bytes)

| Offset | Address | Name | Description |
|---|---|---|---|
| +0 | F605H | `col` | Ball byte-column (0–29) |
| +1 | F606H | `row` | Ball pixel-row (1–60) |
| +2 | F607H | `dx` | Column delta: `01H` = right, `0FFH` = left |
| +3 | F608H | `dy` | Row delta: `01H` = down, `0FFH` = up |
| +4–+7 | F609H–F60CH | `sprite[0..3]` | Ball pattern (4 bytes, 1 per row) |
| +8–+9 | F60DH–F60EH | `delay_ctr` | Frame delay word (0 = max speed) |
| +10 | F60FH | `py` | Left paddle top row (0–52) |
| +11 | F610H | `old_py` | Previous `py` (written by MC each frame) |
| +12 | F611H | `opy` | Right (AI) paddle top row (0–52) |
| +13 | F612H | `old_opy` | Previous `opy` (written by MC each frame) |
| +14 | F613H | `miss` | Miss flag: `00H` = none, `01H` = P1, `02H` = P2 |
| +15 | F614H | `S1` | Player 1 score (0–9, wraps at 10) |
| +16 | F615H | `S2` | Player 2 score (0–9, wraps at 10) |
| +17 | F616H | `score_dirty` | `01H` = redraw scores this frame |

---

## BASIC Loader (lines 6–11)

```basic
6 DIM MC$(452,1)
7 AD=VARPTR(MC$)-1
8 FOR I=0 TO 905:READ V:POKE AD+I,V:NEXT I
9 FOR I=0 TO 50:READ P
10 L=PEEK(AD+P):H=PEEK(AD+P+1):W=L+H*256+AD
11 POKE AD+P,W-INT(W/256)*256:POKE AD+P+1,INT(W/256):NEXT I
```

`DIM MC$(452,1)` allocates ≥ 906 bytes (`(452+1)*2 = 906`).  
`AD = VARPTR(MC$)-1` points one byte before the string data so that  
`POKE AD+0` writes the first MC byte.

**Patch loop** (lines 9–11): for each of the 51 patch offsets in line 961,  
reads the 16-bit little-endian value at `AD+P`, adds `AD`, and writes it back.  
This converts every internal `CALL`/`JP` target from a 0-based offset into an  
absolute address — so BASIC can execute the routine with `CALL(AD)`.

`CALL 0005H` (BDOS) is **not** patched: `0005H` is the live CP/M BDOS vector.

---

## Frame Structure

Each frame (one BASIC `CALL(AD)`) executes these steps:

1. Clear miss flag
2. Erase ball (restore net pixels at column 15 if needed)
3. Conditional score draw (forced if `score_dirty`, skipped if ball is far from top)
4. Left paddle delta update (full redraw if ball column = `PADDLE_COL`)
5. AI: move right paddle toward ball by `PADDLE_SPEED` rows/frame
6. Right paddle delta update (full redraw if ball column = `RIGHT_PADDLE_COL`)
7. Update `col` + bounce/miss detection + score increment + BEL
8. Update `row` + bounce at rows 1 and 60
9. Left paddle collision (bounce `dx` if ball overlaps)
10. Right paddle collision (bounce `dx` if ball overlaps)
11. Draw ball at new position
12. `RET` to BASIC

---

## Subroutines

| Label | Purpose |
|---|---|
| `erase_rows` | Write `00H` to B consecutive VRAM rows from DE |
| `draw_rows` | Write `0FFH` to B consecutive VRAM rows from DE |
| `draw_digit` | Draw one 7-row digit (A=0–9) at column C, rows 0–6 |
| `next_row` | Advance DE by 30 (one LCD pixel-row) |
| `calc_vram` | Compute DE = row×30 + col from A=row, C=col |
| `set_cursor` | Write DE as cursor address to HD61830 (ports 20H/21H) |
| `write_byte` | Write A as display data to HD61830 |
| `wait_busy` | Poll HD61830 port 21H bit 7 until not busy |
| `digit_font` | 70-byte table: 10 digits × 7 rows |

---

## Difficulty Settings

The build (DIFFICULTY = 1, medium) uses:

| Constant | Value | Meaning |
|---|---|---|
| `PADDLE_COL` | 4 | Left paddle at byte-column 4 |
| `RIGHT_PADDLE_COL` | 25 | Right paddle at byte-column 25 |
| `PADDLE_HEIGHT` | 12 | Paddle height in rows |
| `PADDLE_SPEED` | 4 | Rows moved per keypress / AI step |
| `MAX_PADDLE_Y` | 52 | = 64 − PADDLE_HEIGHT |

To regenerate for a different difficulty, change `DIFFICULTY` in `gen_pong2P.py`  
and re-run `python gen_pong2P.py`.
