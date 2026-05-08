# DEFENDER — Z80 Machine Code Notes

See [../../ASM_README.md](../../ASM_README.md) for general workflow, assembler setup,
and the full index of worked examples.

## Files

| File | Description |
|---|---|
| `../Defend.BAS` | Splash screen (MC LCD blast, chains to DefDat1) |
| `../DefDat1.BAS` | Game (DIM/VARPTR loader, runtime patch, CALL) |
| `../gen_defend_splash.py` | Generator for Defend splash |
| `../gen_defdat1.py` | Generator for DefDat1 game (imports Asm from Iterations/) |
| `../../../Dev/defender/Iterations/gen_defend11.py` | Asm class + build_routine() |
| `DEFEND.asm` | Z80 source (Intel-style, sjasmplus compatible) — byte-perfect match |
| `DEFEND.lst` | sjasmplus hex listing (addresses and bytes) |
| `DEFEND.dlst` | Decimal listing (for BASIC DATA transcription) |
| `POKE_LIST.txt` | DATA lines + patch table formatted to match DefDat1.BAS |
| `sprite_data.txt` | Ship/enemy/heart sprite reference with hex/binary/visual rendering |

## Program Summary

`DEFEND.asm` is the Z80 source for the DEFENDER game engine. Assembled with
sjasmplus it produces a 1435-byte binary. The Python generator `gen_defdat1.py`
uses the same logic (via the `Asm` class in `gen_defend11.py`) to emit the same
bytes directly into BASIC DATA lines — the assembled binary and the generator
output are byte-perfect matches.

| Property | Value |
|---|---|
| Binary size | 1435 bytes |
| Generator | `../gen_defdat1.py` (imports `Asm` from `../../Iterations/gen_defend11.py`) |
| Loader pattern | DIM/VARPTR string array (`ORG 0000H` style, patched at runtime) |
| PARAM_BASE | `F605H` = 62981 (fixed user-code area, 53 bytes) |
| Patch table | 118 offsets (CALL/JP targets, BASIC lines 9–11) |

## Assembling

From the workspace root:

```
Assembler\sjasmplus-1.22.0.win\sjasmplus.exe --raw=DEFEND.bin --lst=Progs/DefendERR/DEFEND_ASM/DEFEND.lst Progs/DefendERR/DEFEND_ASM/DEFEND.asm
python Dev/asm_tools/lst_to_dlst.py Progs/DefendERR/DEFEND_ASM/DEFEND.lst
```

## Loader Pattern — DIM/VARPTR with Runtime Patching

```basic
6 DIM MC$(717,1)
7 AD=VARPTR(MC$)-1
8 FOR I=0 TO 1434:READ V:POKE AD+I,V:NEXT I
9 FOR I=0 TO 117:READ P
10 L=PEEK(AD+P):H=PEEK(AD+P+1):W=L+H*256+AD
11 POKE AD+P,W-INT(W/256)*256:POKE AD+P+1,INT(W/256):NEXT I
```

`DIM MC$(717,1)` allocates at least 1435 bytes. `VARPTR` returns the data
area base; subtracting 1 gives `AD` used as code origin.

Lines 9–11 apply 118 runtime patches: each entry is a byte offset `P` into the
MC where an assembled-from-zero 16-bit address needs `AD` added to it.

## Parameter Block Layout (PARAM_BASE = F605H = 62981)

| Offset | Address | Name | Init | Description |
|--------|---------|------|------|-------------|
| +0 | 62981 | ship_row | 28 | Ship Y pixel row (0–56) |
| +1 | 62982 | old_row | 28 | Previous row (redraw guard) |
| +2..+9 | 62983–62990 | ship_sprite | `01 07 1F FF FF 1F 07 01` | 8-byte ship pattern |
| +10 | 62991 | delay_lo | 136 | Frame delay counter low byte |
| +11 | 62992 | delay_hi | 19 | Frame delay counter high byte (4992 total) |
| +12 | 62993 | star1_col | 27 | Star 1 column (0–29) |
| +13 | 62994 | star1_row | 10 | Star 1 row |
| +14 | 62995 | star2_col | 12 | Star 2 column |
| +15 | 62996 | star2_row | 42 | Star 2 row |
| +16 | 62997 | star3_col | 21 | Star 3 column |
| +17 | 62998 | star3_row | 26 | Star 3 row |
| +18 | 62999 | rng_seed | 37 | Pseudo-RNG state byte |
| +19 | 63000 | shot_col | 0 | Projectile column |
| +20 | 63001 | shot_row | 0 | Projectile row |
| +21 | 63002 | shot_active | 0 | 0=inactive, 1=active |
| +22 | 63003 | enemy1_col | 0 | Enemy 1 column |
| +23 | 63004 | enemy1_row | 0 | Enemy 1 row |
| +24 | 63005 | enemy1_active | 0 | 0=inactive, 1=active |
| +25 | 63006 | enemy1_phase | 0 | Frame divider 0–3 (quarter-speed) |
| +26..+33 | 63007–63014 | enemy1_sprite | `1C A0 3E F1 F1 3E A0 1C` | 8-byte enemy pattern |
| +34 | 63015 | enemy1_dy | 1 | Vertical direction: 1=down, 0xFF=up |
| +35 | 63016 | enemy2_col | 0 | Enemy 2 column |
| +36 | 63017 | enemy2_row | 0 | Enemy 2 row |
| +37 | 63018 | enemy2_active | 0 | 0=inactive, 1=active |
| +38 | 63019 | enemy2_phase | 0 | Frame divider 0–3 |
| +39 | 63020 | enemy2_dy | 1 | Vertical direction: 1=down, 0xFF=up |
| +40 | 63021 | kill_count | 0 | Running kill total (also displayed as score) |
| +41 | 63022 | wave | 0 | 0=one enemy, 1=two enemies (triggers at kill 5) |
| +42 | 63023 | lives | 3 | Current lives remaining |
| +43 | 63024 | player_dead | 0 | MC sets 1 on ship-enemy collision; BASIC clears |
| +44..+51 | 63025–63032 | heart_sprite | `36 7E 7E 3C 18 10 00 00` | 8-byte heart icon |
| +52 | 63033 | event_code | 0 | 0=none, 1=laser, 2=explosion, 3=death |

**Total:** 53 bytes (well within the 80-byte user-area limit at F605H).

## Event Code Dispatch

The MC sets `event_code` and returns early (`RET NZ`) at the end of each frame
when a sound event occurs. BASIC dispatches:

```basic
65 Z=CALL(AD)
66 IF PEEK(63024)=1 THEN GOTO 80          ' player_dead -> die path
67 EV=PEEK(63033):IF EV=0 THEN GOTO 100   ' no event -> ESC exit
68 POKE 63033,0:ON EV GOSUB 200,210:GOTO 65
```

| event_code | Meaning | BASIC routine |
|---|---|---|
| 1 | Fire (new laser shot) | 200 — ascending sweep |
| 2 | Explosion (shot hit enemy) | 210 — descending blip |
| 3 | Death (ship-enemy collision) | 220 — slow descending sweep |

## Key Techniques

- **Starfield**: 3 two-pixel stars scroll left each frame; wrap randomises row from RNG seed
- **Enemies**: Diagonal movement — horizontal every 4 frames, vertical every frame; bounce at top/bottom
- **Wave 2**: Second enemy activates when `kill_count` reaches 5 (`wave` byte set to 1)
- **Collision**: Shot-vs-enemy bounding box; ship-vs-enemy column+row overlap
- **Hearts HUD**: 3 hearts drawn at columns 0/1, rows 0/8/16 every frame (erased and redrawn to survive star overwrite)
- **Sound**: BASIC `SOUND` called between MC frames via early RET; game display is fully rendered before sound plays

