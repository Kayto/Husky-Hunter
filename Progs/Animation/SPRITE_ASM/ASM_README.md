# SPRITE — Assembly Notes

SPRITE is a byte-aligned sprite animation using 140 bytes of Z80 machine code.
The MC routine moves an 8×8 ball horizontally across the screen at a fixed
vertical position (row 28, the centre of the 64-row display).

See [Progs/ASM_README.md](../../ASM_README.md) for the general assembly workflow.

## Files

| File | Description |
|---|---|
| `../SPRITE.BAS` | Husky Hunter BASIC program — installs params, MC and runs |
| `../SPRITE.asm` | Z80 source (sjasmplus / Pasmo syntax) |
| `SPRITE.lst` | Hex listing produced by sjasmplus |
| `SPRITE.dlst` | Decimal listing (hex→dec converted via `lst_to_dlst.py`) |
| `POKE_LIST.txt` | DATA lines formatted to match BAS + annotated by section |
| `sprite_data.txt` | Sprite pattern reference with hex/binary/visual rendering |

## What the MC Does

Runs an infinite sprite animation loop until a key is pressed.

Each frame:
1. **Erase** — computes VRAM addr for current column at row 28, writes 0 to 8 LCD rows
2. **Advance** — increments column, wraps at 30
3. **Draw** — computes VRAM addr for new column, writes 8 sprite bytes
4. **Delay** — busy-loops for `delay_ctr` iterations
5. **Key check** — calls BDOS fn11; if key pressed, RET

- **Entry**: no call arguments — all parameters live in `PARAM_BASE` block
- **Exit**: returns normally on keypress; otherwise loops forever
- **Loaded at**: `F605H` (62981) — 140 bytes

VRAM address = `840 + col` (Y_BASE = row 28 × 30 = 840, fixed).

## Parameter Block (`PARAM_BASE = F740H = 63296`)

| Offset | Address | Value | Description |
|--------|---------|-------|-------------|
| +0 | 63296 | 14 | `col` — current column (0–29), updated each frame |
| +1..+8 | 63297–63304 | see below | 8-byte sprite pattern |
| +9..+10 | 63305–63306 | 160, 15 | `delay_ctr` word (little-endian) = `0x0FA0` = 4000 |

Sprite pattern (solid oval): `60,126,255,255,255,255,126,60`

## BDOS Call

`CALL 0005H` with `C=0BH` (console status) is used for the keypress check —
fixed CP/M BDOS entry point, not patched by the BASIC loader.

## DE += 30 Trick

The Z80 has no `ADD DE,nn`. Row advancement uses:
```
LD H,D / LD L,E / LD BC,30 / ADD HL,BC / EX DE,HL
```

## Double-EX Trick (draw_loop)

SPRITE uses `EX DE,HL` twice around `ADD HL,BC` to advance DE (VRAM addr)
by 30 while preserving HL (sprite pointer):
```
EX DE,HL          ; HL = VRAM, DE = sprite ptr
LD BC,30
ADD HL,BC         ; HL = VRAM + 30
EX DE,HL          ; DE = VRAM+30, HL = sprite ptr  (both preserved)
```

## Assembling

From the repository root:

```
Assembler\sjasmplus-1.22.0.win\sjasmplus.exe --raw=Progs/Animation/SPRITE.bin --lst=Progs/Animation/SPRITE_ASM/SPRITE.lst Progs/Animation/SPRITE.asm
```

140 bytes, 0 errors.

## Create Decimal Listing

```
python Dev/asm_tools/lst_to_dlst.py Progs/Animation/SPRITE_ASM/SPRITE.lst
```

## DATA Lines

```
899 REM === Z80 machine code: 140 bytes (addr 62981-63120) ===
900 DATA  58, 64,247, 95, 22,  0, 33, 72,  3, ...  (15 per line, lines 900-909)
```

See `SPRITE_ASM/POKE_LIST.txt` for the full annotated byte list.

## HBA Note

The HBA (tokenized BASIC) stores the DATA arguments as ASCII decimal text —
the MC bytes have no binary presence in the `.HBA` file.
