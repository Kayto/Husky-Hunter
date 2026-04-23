# Z80 Machine Code Embedded in BASIC

Several BASIC programs on the Husky Hunter contain inline Z80 machine code,
POKEd into memory and invoked with `CALL`. The `.asm` source files in each
program subfolder are the canonical, human-readable source for that code.

For ease of `.BAS` creation and parameter adjustment during development various `gen_ .py` python scripts have been created to wrap and automate the handling of BASIC and machine code. However this wrapping makes the content difficult to openly read and adapt for different examples. Therefore I share the raw asm, listings and decimal conversions to allow manual adjustment outside of the python wrappers.  

## Files

| `.asm` file | BASIC program | Bytes |
|---|---|---|
| `Animation/SPRITE.asm` | `SPRITE.BAS` | 140 |
| `Animation/BOUNCE.asm` | `BOUNCE.BAS` | ~158 + 30-byte wave table |
| `Animation/BOUNCE2.asm` | `BOUNCE2.BAS` | ~212 + 30-byte wave table |
| `Animation/PONG.asm` | `PONG.BAS` | 199 |
| `image_writer/IMGMC.asm` | `IMGMC.BAS` | 30 |
| `machine_code/COLLATMC.asm` | `COLLATMC.BAS` | 33 |
| `pong/PONGGAME_ASM/PONGGAME.asm` | `PONGGAME.BAS` | 451 |


## Two Loader Patterns

Two loader patterns are utilised for machine code.

### Fixed user-code area (`ORG 0F605H`)
Used by: SPRITE, BOUNCE, BOUNCE2, PONG, IMGMC, COLLATMC

BASIC POKEs bytes into the fixed user code area at `0F605H` (62981 decimal):

```basic
FOR I=0 TO N: READ V: POKE 62981+I,V: NEXT I
CALL 62981
```

Parameters are passed via a block at `0F740H` (63296):

```basic
POKE 63296, col
POKE 63297, row
```

Because `ORG 0F605H`, every label in the assembled binary resolves to its final
real address. The raw output bytes are exactly the DATA values in the BASIC
program.

### DIM/VARPTR string array (`ORG 0000H`)
Used by: PONGGAME only

BASIC allocates a string array, takes its address, and POKEs the code there:

```basic
DIM MC$(D,1)
AD = VARPTR(MC$) - 1
POKE AD+I, V
CALL AD
```

Because the load address is not known at assembly time, the code is assembled
with `ORG 0000H`. All internal `CALL`/`JP` targets in the assembled binary are
offsets from zero. BASIC calculates the real load address at runtime and patches
every target before calling the code.

> **Note:** `CALL 0005H` (CP/M BDOS entry point) in PONGGAME is **not** patched
> — `0005H` is the real CP/M BDOS vector and is always valid.

## Manual Workflow

### Assembler

sjasmplus is **not included** in the repository (`Assembler/` is gitignored).
Download the Windows release from https://github.com/z00m128/sjasmplus/releases
and extract it so the executable is at:

```
Assembler/sjasmplus-1.22.0.win/sjasmplus.exe
```

The `.asm` files use standard Z80 syntax compatible with sjasmplus and Pasmo.
GNU as (GAS) and NASM are x86 assemblers and will not work.

### Assembling a Program

Produce a raw binary and a hex listing in one pass:

```
Assembler\sjasmplus-1.22.0.win\sjasmplus.exe --raw=PROG.bin --lst=PROG.lst PROG.asm
```

This produces:
- `PROG.bin` — raw bytes, directly comparable to the BASIC POKE values
- `PROG.lst` — annotated listing with hex addresses and hex bytes

### Decimal Listing (for creating BASIC Data/Poke lines)

Use `Dev/asm_tools/lst_to_dlst.py` to convert a hex `.lst` to a decimal `.dlst`:

```
python Dev/asm_tools/lst_to_dlst.py PROG.lst
```

Addresses and opcode bytes are converted to decimal for translation to
BASIC DATA / POKE values.

### Create your BASIC listing

With the `.dlst` in hand, the bytes can be transcribed into BASIC DATA or POKE
statements. Choose the loader pattern that suits your program:

**Fixed user-code area** (`ORG 0F605H`) — simplest, use for standalone routines:

```basic
900 REM === Z80 machine code ===
900 DATA 99,105,6,0, ...        : REM up to 15 values per DATA line
...
5 FOR I=0 TO N: READ V: POKE 62981+I,V: NEXT I
```

**Inline POKE** — for short routines (e.g. 33 bytes in 3 lines):

```basic
32 POKE 62981, 99,105, 6, 0,124,183, 32, 5,125,254,  1
34 POKE 62992, 40, 18, 4,203, 69, 32, 6,203, 60,203, 29
36 POKE 63003, 24,236,229, 41,209, 25, 35, 24,229,120,201
```

**Calling the routine** — pass parameters then CALL the load address:

```basic
REM No return value:
P = ARG(0) : Z = CALL(62981)

REM Return value in A (e.g. step count, status byte):
P = ARG(param) : result = CALL(62981)

REM Parameters via PARAM_BASE block (F740H = 63296):
POKE 63296, col
POKE 63297, row
Z = CALL(62981)
```

`ARG(x)` loads the 16-bit value `x` into the BC/DE registers before the CALL.
`CALL(addr)` invokes the routine and returns the value left in register A.

## Worked Examples

If you dont understand the above, take a look at the following to give some working examples.

| Program | Bytes | Notes | README |
|---|---|---|---|
| COLLATMC | 33 | Simplest example: inline POKE, ARG/CALL return value, no external data | [COLLATMC/ASM_README.md](machine_code/COLLATMC/ASM_README.md) |
| IMGMC | 30 | DATA/POKE loop, hard-coded HL/DE, two-phase (image load + MC blast) | [image_writer/IMGMC_ASM/ASM_README.md](image_writer/IMGMC_ASM/ASM_README.md) |
| SPRITE | 140 | Parameter block, fixed-row horizontal movement, double-EX trick; `sprite_data.txt` included | [Animation/SPRITE_ASM/ASM_README.md](Animation/SPRITE_ASM/ASM_README.md) |
| BOUNCE | 188 | Parameter block, wave table, BDOS call, two DATA sections (MC + wave); `sprite_data.txt` included | [Animation/BOUNCE_ASM/ASM_README.md](Animation/BOUNCE_ASM/ASM_README.md) |
| BOUNCE2 | 242 | Two sprites, shared erase_at subroutine, opposing directions; `sprite_data.txt` included | [Animation/BOUNCE2_ASM/ASM_README.md](Animation/BOUNCE2_ASM/ASM_README.md) |
| PONG | 199 | Diagonal bounce, signed delta bytes, NEG direction reversal; `sprite_data.txt` included | [Animation/PONG_ASM/ASM_README.md](Animation/PONG_ASM/ASM_README.md) |
| PONGGAME | 451 | DIM/VARPTR loader, runtime CALL/JP patching (33 offsets), full paddle game; `sprite_data.txt` included | [pong/PONGGAME_ASM/ASM_README.md](pong/PONGGAME_ASM/ASM_README.md) |
