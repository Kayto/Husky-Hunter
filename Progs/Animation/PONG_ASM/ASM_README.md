# PONG — Assembly Notes

PONG is a 4×4 ball bouncing demo using 199 bytes of Z80 machine code.
The ball moves diagonally, bouncing off all four edges of the 240×64 LCD display.

See [Progs/ASM_README.md](../../ASM_README.md) for the general assembly workflow.

## Files

| File | Description |
|---|---|
| `../PONG.BAS` | Husky Hunter BASIC program — installs params, MC and runs |
| `../PONG.asm` | Z80 source (sjasmplus / Pasmo syntax) |
| `PONG.lst` | Hex listing produced by sjasmplus |
| `PONG.dlst` | Decimal listing (hex→dec converted via `lst_to_dlst.py`) |
| `POKE_LIST.txt` | DATA lines formatted to match BAS + annotated by section |
| `sprite_data.txt` | Sprite pattern reference with hex/binary/visual rendering |

## What the MC Does

Runs an infinite ball-bounce animation loop until a key is pressed.

Each frame:
1. **Erase** — computes VRAM addr for current (col, row), writes 0 to 4 LCD rows
2. **Bounce col** — adds `dx` to `col`; if result ≥ 30, negates `dx` and recomputes
3. **Bounce row** — adds `dy` to `row`; if result ≥ 61, negates `dy` and recomputes
4. **Draw** — computes VRAM addr for new position, writes 4 sprite bytes
5. **Delay** — busy-loops for `delay_ctr` iterations
6. **Key check** — calls BDOS fn11; if key pressed, RET

- **Entry**: no call arguments — all parameters live in `PARAM_BASE` block
- **Exit**: returns normally on keypress; otherwise loops forever
- **Loaded at**: `F605H` (62981) — 199 bytes

## Parameter Block (`PARAM_BASE = F740H = 63296`)

| Offset | Address | Value | Description |
|--------|---------|-------|-------------|
| +0 | 63296 | 14 | `col` — byte column (0–29) |
| +1 | 63297 | 30 | `row` — pixel row (0–60) |
| +2 | 63298 | 1 | `dx` — column delta (`1` or `0FFH` = -1) |
| +3 | 63299 | 1 | `dy` — row delta (`1` or `0FFH` = -1) |
| +4..+7 | 63300–63303 | 24,60,60,24 | 4-byte sprite pattern |
| +8..+9 | 63304–63305 | 208, 7 | `delay_ctr` word (little-endian) = `0x07D0` = 2000 |

Sprite pattern (`24,60,60,24`): a 4×4 diamond / blob.

## Bounce Algorithm

Direction bytes (`dx`, `dy`) are signed 8-bit values stored as unsigned: `1` or `255` (-1).
Bounce is detected with unsigned `CP MAX+1`:
- If `col + dx >= 30` (unsigned), negate `dx` and recompute `col`
- If `row + dy >= 61` (unsigned), negate `dy` and recompute `row`

`NEG` is used to reverse the direction byte in-place.

## calc_vram

Takes `A` = row, `C` = col; returns `DE` = VRAM byte offset.

```
VRAM offset = row * 30 + col
```

`row * 30` is computed as `row * 32 − row * 2` (shifts + `SBC HL,DE`).

Note: The Z80 has no `LD C,(nn)` — parameters must be loaded via A and shuffled
into place with extra moves before calling `calc_vram`.

## BDOS Call

`CALL 0005H` with `C=0BH` (console status) — fixed CP/M BDOS entry, not patched.

## Assembling

From the repository root:

```
Assembler\sjasmplus-1.22.0.win\sjasmplus.exe --raw=Progs/Animation/PONG.bin --lst=Progs/Animation/PONG_ASM/PONG.lst Progs/Animation/PONG.asm
```

199 bytes, 0 errors.

## Create Decimal Listing

```
python Dev/asm_tools/lst_to_dlst.py Progs/Animation/PONG_ASM/PONG.lst
```

## DATA Lines

```
899 REM === Z80 machine code: 199 bytes (addr 62981-63179) ===
900 DATA  58, 65,247, 79, 58, 64,247, 71,121, 72,205,137,246,  6,  4
...                                                (15 per line, lines 900-913)
```

See `PONG_ASM/POKE_LIST.txt` for the full annotated byte list.

## HBA Note

The HBA (tokenized BASIC) stores the DATA arguments as ASCII decimal text —
the MC bytes have no binary presence in the `.HBA` file.
