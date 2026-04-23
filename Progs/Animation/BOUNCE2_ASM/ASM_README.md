# BOUNCE2 — Assembly Notes

BOUNCE2 is a two-sprite wave animation using 212 bytes of Z80 machine code
plus a 30-byte sine-derived wave table, 242 bytes total.
A circle moves right while a diamond moves left; both follow the same sine curve.

See [Progs/ASM_README.md](../../ASM_README.md) for the general assembly workflow.

## Files

| File | Description |
|---|---|
| `../BOUNCE2.BAS` | Husky Hunter BASIC program — installs params, MC, wave table and runs |
| `../BOUNCE2.asm` | Z80 source (sjasmplus / Pasmo syntax) |
| `BOUNCE2.lst` | Hex listing produced by sjasmplus |
| `BOUNCE2.dlst` | Decimal listing (hex→dec converted via `lst_to_dlst.py`) |
| `POKE_LIST.txt` | DATA lines formatted to match BAS + annotated by section |
| `sprite_data.txt` | Both sprite patterns (circle + diamond) with hex/binary/visual rendering |

## What the MC Does

Runs an infinite two-sprite animation loop until a key is pressed.

Each frame:
1. **Erase** — calls `erase_at(col1)` then `erase_at(col2)`
2. **Advance** — `col1` increments right (wrap 29→0); `col2` decrements left (wrap 0→29)
3. **Draw sprite1** — `calc_vram(col1)`, write 8 rows from `sprite1` pattern
4. **Draw sprite2** — `calc_vram(col2)`, write 8 rows from `sprite2` pattern
5. **Delay** — busy-loops for `delay_ctr` iterations
6. **Key check** — calls BDOS fn11; if key pressed, RET

- **Entry**: no call arguments — all parameters live in `PARAM_BASE` block
- **Exit**: returns normally on keypress; otherwise loops forever
- **Loaded at**: `F605H` (62981) — 212 bytes code + 30 bytes wave table = 242 bytes total

## Parameter Block (`PARAM_BASE = F740H = 63296`)

| Offset | Address | Value | Description |
|--------|---------|-------|-------------|
| +0 | 63296 | 0 | `col1` — sprite 1 column (moves right, wraps 29→0) |
| +1 | 63297 | 15 | `col2` — sprite 2 column (moves left, wraps 0→29) |
| +2..+9 | 63298–63305 | see below | `sprite1` pattern — circle (8 bytes) |
| +10..+17 | 63306–63313 | see below | `sprite2` pattern — diamond (8 bytes) |
| +18..+19 | 63314–63315 | 160, 15 | `delay_ctr` word (little-endian) = `0x0FA0` = 4000 |

Sprite1 (circle): `60,126,255,255,255,255,126,60`
Sprite2 (diamond): `24,60,126,255,126,60,24,0`

## erase_at Subroutine

Shared erase routine: takes column in `A`, calls `calc_vram`, erases 8 rows.
This avoids duplicating the erase logic for two sprites (saves ~20 bytes vs
two inline erase loops).

## calc_vram

```
VRAM offset = wave_table[col] * 30 + col
```

`row * 30` computed as `row * 32 − row * 2` (shifts + `SBC HL,DE`).
`wave_table` is embedded at the end of the MC binary (addr `F6D9H` = 63193).

## Wave Table

30 bytes at the end of the MC block. Same sine values as BOUNCE:

```
Formula: int(28 + 20 * sin(col * 2π / 30))
```

Regenerate via `gen_bounce2.py`.

## BDOS Call

`CALL 0005H` with `C=0BH` — fixed CP/M BDOS entry, not patched by the BASIC loader.

## BASIC Program Structure

**Load MC + wave table** (line 6):
```
FOR I=0 TO 241:READ V:POKE 62981+I,V:NEXT I
```
Reads 212 MC bytes (DATA 900–914) then 30 wave table bytes (DATA 920–922)
in one pass. The `REM` at line 915 is skipped; READ continues into line 920.

**Set parameters** (lines 10–29): POKEs col1=0, col2=15, both sprite patterns,
and delay counter to `PARAM_BASE` block.

**Run MC** (line 30):
```
P=ARG(0):Z=CALL(62981)
```

## Assembling

From the repository root:

```
Assembler\sjasmplus-1.22.0.win\sjasmplus.exe --raw=Progs/Animation/BOUNCE2.bin --lst=Progs/Animation/BOUNCE2_ASM/BOUNCE2.lst Progs/Animation/BOUNCE2.asm
```

242 bytes, 0 errors.

## Create Decimal Listing

```
python Dev/asm_tools/lst_to_dlst.py Progs/Animation/BOUNCE2_ASM/BOUNCE2.lst
```

## DATA Lines

```
899 REM === Z80 machine code: 212 bytes (addr 62981-63192) ===
900 DATA  58, 64,247,205,117,246, ...  (15 per line, lines 900-914)
914 DATA 251,201
915 REM === Wave table: sine row per col 0-29 ===
920 DATA  28, 32, 36, 39, 42, 45, 47, 47, 47, 47
921 DATA  45, 42, 39, 36, 32, 28, 23, 19, 16, 13
922 DATA  10,  8,  8,  8,  8, 10, 13, 16, 19, 23
```

See `BOUNCE2_ASM/POKE_LIST.txt` for the full annotated byte list.

## HBA Note

The HBA (tokenized BASIC) stores the DATA arguments as ASCII decimal text —
the MC bytes have no binary presence in the `.HBA` file.
