# BOUNCE — Assembly Notes

BOUNCE is a wave-motion sprite animation using 188 bytes of Z80 machine code.
The MC routine erases and redraws an 8×8 ball each frame, with the vertical
position driven by a 30-entry sine-derived wave table embedded after the code.

See [Progs/ASM_README.md](../../ASM_README.md) for the general assembly workflow.

## Files

| File | Description |
|---|---|
| `BOUNCE.BAS` | Husky Hunter BASIC program — installs params, MC, wave table and runs |
| `BOUNCE_ASM/BOUNCE.asm` | Z80 source (sjasmplus / Pasmo syntax) |
| `BOUNCE_ASM/BOUNCE.lst` | Hex listing produced by sjasmplus |
| `BOUNCE_ASM/BOUNCE.dlst` | Decimal listing (hex→dec converted via `lst_to_dlst.py`) |
| `BOUNCE_ASM/POKE_LIST.txt` | DATA lines formatted to match BAS + annotated by section |
| `BOUNCE_ASM/sprite_data.txt` | Sprite pattern reference with binary/visual rendering |

## What the MC Does

Runs an infinite sprite animation loop until a key is pressed.

Each frame:
1. **Erase** — reads current column, calls `calc_vram`, writes 0 to 8 LCD rows
2. **Advance** — increments column, wraps at 30
3. **Draw** — calls `calc_vram` for new position, writes 8 sprite bytes
4. **Delay** — busy-loops for `delay_ctr` iterations
5. **Key check** — calls BDOS fn11 (console status); if key pressed, RET

- **Entry**: no call arguments — all parameters live in `PARAM_BASE` block
- **Exit**: returns normally on keypress; otherwise loops forever
- **Loaded at**: `F605H` (62981) — 158 bytes of code + 30 bytes wave table = 188 bytes total

## Parameter Block (`PARAM_BASE = F740H = 63296`)

Set by BASIC POKEs before calling the MC:

| Offset | Address | Value | Description |
|--------|---------|-------|-------------|
| +0 | 63296 | 0 | `col` — current column (0–29), updated each frame |
| +1..+8 | 63297–63304 | see sprite_data.txt | 8-byte sprite pattern |
| +9..+10 | 63305–63306 | 160, 15 | `delay_ctr` word (little-endian) = `0x0FA0` = 4000 |

The sprite pattern is a solid oval: rows `60,126,255,255,255,255,126,60`.

## BDOS Call

`CALL 0005H` with `C=0BH` (console status) is used for the keypress check.
This is a CP/M BDOS call and is **not patched** by the BASIC loader — `0005H`
is the fixed CP/M BDOS entry point in DEMOS 2.2.

## calc_vram Subroutine

Computes the HD61830 VRAM byte offset for a given column and sine-table row:

```
VRAM offset = wave_table[col] * 30 + col
```

`row * 30` is computed as `row * 32 − row * 2` using shifts and `SBC HL,DE`
(avoids a multiply instruction; the Z80 has none).

## Wave Table

30 bytes embedded at the end of the MC block (`wave_table` label), immediately
following the code. The table contains the Y row for each column:

```
Formula: int(28 + 20 * sin(col * 2π / 30))
```

Loaded into the same FOR/READ/POKE loop as the MC, and POKEd to `F69DH`–`F6BAH`
(63133–63162). Regenerate by editing `WAVE_CENTRE` / `WAVE_AMPLITUDE` in
`gen_bounce.py`.

## BASIC Program Structure

**Load MC + wave table** (line 6):
```
FOR I=0 TO 187:READ V:POKE 62981+I,V:NEXT I
```
Reads 158 MC bytes (DATA 900–910) then 30 wave table bytes (DATA 920–922) in
one pass. The two blocks are separated by line 915 `REM` but the READ pointer
advances continuously through both.

**Set sprite parameters** (lines 9–20):
```
POKE 63296,0          : REM col = 0
POKE 63297,60  ...    : REM sprite pattern (8 bytes)
POKE 63305,160:POKE 63306,15  : REM delay counter = 4000
```

**Run MC** (line 30):
```
P=ARG(0):Z=CALL(62981)
```
`ARG(0)` is a no-op here (parameters are already in RAM); `CALL(62981)` invokes the routine.

## Assembling

From the repository root:

```
Assembler\sjasmplus-1.22.0.win\sjasmplus.exe --raw=Progs/Animation/BOUNCE.bin --lst=Progs/Animation/BOUNCE_ASM/BOUNCE.lst Progs/Animation/BOUNCE_ASM/BOUNCE.asm
```

188 bytes, 0 errors.

## Create Decimal Listing

```
python Dev/asm_tools/lst_to_dlst.py Progs/Animation/BOUNCE_ASM/BOUNCE.lst
```

Produces `BOUNCE_ASM/BOUNCE.dlst` with addresses and bytes in decimal.

## DATA Lines

The 188 bytes are split across two DATA blocks in `BOUNCE.BAS`:

```
899 REM === Z80 machine code: 158 bytes (addr 62981-63138) ===
900 DATA  58, 64,247,205, 87,246, ...  (15 per line, lines 900-910)
915 REM === Wave table: sine row per col 0-29 ===
920 DATA  28, 32, 36, 39, 42, 45, 47, 47, 47, 47
921 DATA  45, 42, 39, 36, 32, 28, 23, 19, 16, 13
922 DATA  10,  8,  8,  8,  8, 10, 13, 16, 19, 23
```

See `BOUNCE_ASM/POKE_LIST.txt` for the full annotated byte list.

## HBA Note

The HBA (tokenized BASIC) stores the DATA arguments as ASCII decimal text —
the MC bytes have no binary presence in the `.HBA` file. They only exist in
memory after the DATA/POKE lines execute at runtime.
