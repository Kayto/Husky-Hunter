# IMGMC — Assembly Notes

IMGMC is the machine code LCD blast routine used by `IMGMC.BAS` to write a
full-screen image to the Husky Hunter display at hardware speed.

See [Progs/ASM_README.md](../../ASM_README.md) for the general assembly workflow.

## Files

| File | Description |
|---|---|
| `../IMGMC.BAS` | Husky Hunter BASIC program — loads image data and runs the MC |
| `../IMGMC.asm` | Z80 source (sjasmplus / Pasmo syntax) |
| `IMGMC.lst` | Hex listing produced by sjasmplus |
| `IMGMC.dlst` | Decimal listing (hex→dec converted via `lst_to_dlst.py`) |
| `POKE_LIST.txt` | Byte list formatted as BASIC DATA statement + annotated |

## What the MC Does

Blasts a 1920-byte image buffer from RAM to the HD61830 LCD controller via I/O.

- **Entry**: no parameters — source address (`C000H`) and length (`0780H`) are hard-coded
- **Exit**: returns normally; display shows the image
- **Buffer**: `C000H`–`C77FH` (1920 bytes = 30 cols × 64 rows)
- **Ports**: `20H` = HD61830 data, `21H` = HD61830 command/status

The routine polls the HD61830 busy flag (port `21H` bit 7) before each command
and each data write. The HD61830 auto-increments its display address register
after every `CMD_WRITE` byte, so no per-byte cursor positioning is needed.

`wait_busy` is inlined at both call sites (saves 2 bytes vs a subroutine; exact
byte-for-byte match with the original `gen_imgmc.py` output).

Loaded at `F605H` (62981) — the fixed user code area reserved by the OS.

## BASIC Program Structure

`IMGMC.BAS` operates in two phases:

**Phase 1 — Load MC** (line 6):
```
FOR I=0 TO 29:READ V:POKE 62981+I,V:NEXT I
```
Reads 30 bytes from `DATA 900` and POKEs them to `F605H`.

**Phase 1 — Load image** (lines 8–10):
```
FOR I=49152 TO 51071
READ V:POKE I,V
NEXT I
```
Reads 1920 bit-reversed image bytes from `DATA 1000+` and POKEs them to the
buffer at `C000H`–`C77FH`. Bit-reversal is pre-computed by `gen_imgmc.py`.

**Phase 2 — Set HD61830 cursor to origin** (lines 12–13):
```
OUT 33,10:OUT 32,0
OUT 33,11:OUT 32,0
```
Sets display address registers X and Y to 0 before the blast.

**Phase 2 — Run MC** (line 14):
```
P=ARG(0):X=CALL(62981)
```
`ARG(0)` is a no-op here (no parameters needed); `CALL(62981)` invokes the routine.

## Assembling

From the repository root:

```
Assembler\sjasmplus-1.22.0.win\sjasmplus.exe --raw=Progs/image_writer/IMGMC.bin --lst=Progs/image_writer/IMGMC_ASM/IMGMC.lst Progs/image_writer/IMGMC.asm
```

30 bytes, 0 errors.

## Create Decimal Listing

```
python Dev/asm_tools/lst_to_dlst.py Progs/image_writer/IMGMC_ASM/IMGMC.lst
```

Produces `IMGMC_ASM/IMGMC.dlst` with addresses and bytes in decimal.

## DATA Line

The 30 MC bytes appear in `IMGMC.BAS` at line 900:

```
900 DATA 33,0,192,17,128,7,219,33,7,56,251,62,12,211,33,219,33,7,56,251,126,211,32,35,27,122,179,32,233,201
```

See `IMGMC_ASM/POKE_LIST.txt` for the full annotated byte list.

## HBA Note

The HBA (tokenized BASIC) stores the DATA arguments as ASCII decimal text —
the MC bytes have no binary presence in the `.HBA` file. They only exist in
memory after the DATA/POKE lines execute at runtime.
