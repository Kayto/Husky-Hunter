# PONGGAME — Z80 Machine Code Notes

See [../../ASM_README.md](../../ASM_README.md) for general workflow, assembler setup,
and the full index of worked examples.

## Files

| File | Description |
|---|---|
| `../PONGGAME.BAS` | BASIC program (DIM/VARPTR loader, runtime patch, CALL) |
| `PONGGAME.asm` | Z80 source (Intel-style, sjasmplus/Pasmo compatible) |
| `PONGGAME.lst` | sjasmplus hex listing (addresses and bytes) |
| `PONGGAME.dlst` | Decimal listing (for BASIC DATA transcription) |
| `POKE_LIST.txt` | DATA lines + patch table formatted to match BAS |
| `sprite_data.txt` | Ball sprite and paddle param reference with hex/binary/visual rendering |

## Program Summary

PONGGAME is a full pong game: a bouncing ball, a solid net (column 15), and a
12-pixel paddle at column 1 controlled with A/Z keys (ESC to exit).

| Property | Value |
|---|---|
| Binary size | 451 bytes |
| Loader pattern | DIM/VARPTR string array (`ORG 0000H`) |
| PARAM_BASE | `F605H` = 62981 (fixed user-code area, 12 bytes) |
| Patch table | 33 offsets (CALL/JP targets, line 940) |

## Loader Pattern — DIM/VARPTR with Runtime Patching

Unlike the other MC programs (which use `ORG 0F605H`), PONGGAME is assembled
with `ORG 0000H`. The code is stored in a BASIC string array at a dynamic
address, so all internal `CALL`/`JP` targets are **offsets from zero** and must
be fixed up at runtime before the code can run.

### Step 1 — Allocate and load MC bytes

```basic
6 DIM MC$(225,1)
7 AD=VARPTR(MC$)-1
8 FOR I=0 TO 450:READ V:POKE AD+I,V:NEXT I
```

`DIM MC$(225,1)` allocates at least 451 bytes. `VARPTR` returns the address of
the string array's data area; subtracting 1 gives the base address `AD` used
as the code origin.

### Step 2 — Patch internal CALL/JP targets

```basic
9 FOR I=0 TO 32:READ P
10 L=PEEK(AD+P):H=PEEK(AD+P+1):W=L+H*256+AD
11 POKE AD+P,W-INT(W/256)*256:POKE AD+P+1,INT(W/256):NEXT I
```

The patch table (DATA line 940) contains 33 byte offsets. At each offset the
assembled binary holds the offset-from-zero of the target label. Lines 9–11
read each offset `P`, load the two-byte target `W = offset + AD`, and write it
back as a real address.

> **Exception:** `CALL 0005H` (CP/M BDOS) is **not** in the patch table — `0005H`
> is the real BDOS vector and needs no adjustment.

### Step 3 — Set parameters and call

```basic
13 REM === Set ball/paddle params (PARAM_BASE = F605H = 62981) ===
14 POKE 62981,14    : REM col  (start column 14)
15 POKE 62982,30    : REM row  (start row 30)
16 POKE 62983,1     : REM dx   (+1 = moving right)
17 POKE 62984,1     : REM dy   (+1 = moving down)
18 POKE 62985,24    : REM sprite[0]
19 POKE 62986,60    : REM sprite[1]
20 POKE 62987,60    : REM sprite[2]
21 POKE 62988,24    : REM sprite[3]
22 POKE 62989,16    : REM delay lo  } 0x2710 = 10000
23 POKE 62990,39    : REM delay hi  }
24 POKE 62991,26    : REM py (initial paddle Y row)
30 DEFSEG=0:P=ARG(0):Z=CALL(AD)
```

Note `PARAM_BASE` here is `F605H` = 62981 — the **fixed user-code area** — used
purely as a parameter block. The MC code itself lives in the DIM array at `AD`.

## Parameter Block Layout (PARAM_BASE = F605H = 62981)

| Offset | Address | Name | Description |
|---|---|---|---|
| +0 | 62981 | col | Ball column (0–29) |
| +1 | 62982 | row | Ball pixel row (0–60) |
| +2 | 62983 | dx | Column delta (1 or 255 = −1) |
| +3 | 62984 | dy | Row delta (1 or 255 = −1) |
| +4–+7 | 62985–62988 | sprite | 4 ball pattern bytes |
| +8–+9 | 62989–62990 | delay | Frame delay counter (little-endian word) |
| +10 | 62991 | py | Paddle Y position (0–52) |
| +11 | 62992 | old_py | Previous py, written by MC each frame |

## Assembling

```
Assembler\sjasmplus-1.22.0.win\sjasmplus.exe --raw=PONGGAME.bin --lst=PONGGAME_ASM\PONGGAME.lst Progs\pong\PONGGAME_ASM\PONGGAME.asm
python Dev\asm_tools\lst_to_dlst.py PONGGAME_ASM\PONGGAME.lst
```

Produces 451 bytes. Compare against BAS DATA lines 900–930:

```python
import re
bas = open('PONGGAME.BAS').read()
data_vals = []
for ln in bas.splitlines():
    m = re.match(r'^(9[0-2]\d|930) DATA (.+)', ln.strip())
    if m:
        data_vals += [int(x.strip()) for x in m.group(2).split(',')]
bdata = list(open('PONGGAME.bin','rb').read())
assert data_vals == bdata, "mismatch!"
```

## Key Techniques

**Differential paddle update** — only the PADDLE_SPEED rows that change are
erased/redrawn each frame, keeping flicker minimal.

**Net preservation** — when erasing the ball, if the ball column equals NET_COL
(15), the net byte (0x18) is restored instead of zeroing.

**Paddle fix on overlap** — if the ball erases pixels from the paddle column,
the full paddle is redrawn before the differential update, ensuring the paddle
never partially disappears.

**Signed direction bytes** — `dx`/`dy` use 0xFF for −1 (unsigned 255 wraps
around). `NEG` reverses direction; the value is written back to the param block.

**Paddle collision** — checked when `col == PADDLE_COL` and `dx == 0FFH` (moving
left). If `row+3 >= py` and `row < py+12`, ball reverses direction.
