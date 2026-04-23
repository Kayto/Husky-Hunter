# COLLATMC — Worked Assembly Example

COLLATMC is the worked example for the Z80 machine code assembly workflow.
It is the simplest MC program in the repository: 33 bytes, no subroutines,
no parameter block, no external data — ideal as a first test.

See [Progs/ASM_README.md](../../ASM_README.md) for the general workflow that
this example demonstrates.

## Files

| File | Description |
|---|---|
| `COLLATMC.BAS` | Husky Hunter BASIC program — installs and runs the MC |
| `ASM/COLLATMC.asm` | Z80 source (sjasmplus / Pasmo syntax) |
| `ASM/COLLATMC.lst` | Hex listing produced by sjasmplus |
| `ASM/COLLATMC.dlst` | Decimal listing (hex→dec converted via `lst_to_dlst.py`) |
| `ASM/POKE_LIST.txt` | Byte list formatted as BASIC POKE statements + annotated |

## What the MC Does

Runs the Collatz sequence on a 16-bit seed and returns the step count in A.

- **Entry**: `E` = seed high byte, `C` = seed low byte (set by `ARG`)
- **Exit**: `A` = step count (returned by `CALL`)
- **Limit**: seed intermediates must stay within 16 bits; step count ≤ 255
- **Safe test seeds**: 27 (111 steps), 97 (118 steps), 171 (124 steps)

Loaded at `F605H` (62981) — the fixed user code area reserved by the OS.

## Assembling

```
Assembler\sjasmplus-1.22.0.win\sjasmplus.exe --raw=ASM/COLLATMC.bin --lst=ASM/COLLATMC.lst ASM/COLLATMC.asm
```

33 bytes, 0 errors.

## Create Decimal Listing

```
python Dev/asm_tools/lst_to_dlst.py ASM/COLLATMC.lst
```

Produces `ASM/COLLATMC.dlst` with addresses and bytes in decimal for creation of the POKE values in COLLATMC.BAS.

## Translate decimal list to BASIC Data/Poke lines

The decimal listing is then translated into POKE statements for inclusion in the `.BAS` file:

```
POKE 62981, 99,105,  6,  0,124,183, 32,  5,125,254,  1
POKE 62992, 40, 18,  4,203, 69, 32,  6,203, 60,203, 29
POKE 63003, 24,236,229, 41,209, 25, 35, 24,229,120,201
```

See `ASM/POKE_LIST.txt` for the full annotated byte list.

## HBA Note

The HBA (tokenized BASIC) stores the POKE arguments as ASCII decimal text —
the MC bytes have no binary presence in the `.HBA` file. They only exist in
memory after the POKE lines execute at runtime.
