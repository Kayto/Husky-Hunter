#!/usr/bin/env python3
"""gen_defdat1.py - Generate DefDat1.BAS/HBA for Prerelease.
By Kayto April 2026
Licensed under the MIT License. See LICENSE file for details.

DefDat1 = DEFEND11 with two Prerelease modifications:

  1. SPLASH PERSISTENCE:
       Line 5: CUROFF only (no SCREEN 1) — LCD retains the Defend splash image
       while all DIM/POKE/patch lines execute.
       Line 64: SCREEN 1 moved here, fires just before the first CALL(AD).
       Mirrors the DEFEND7/DEFEND7B arrangement.

  2. GAME OVER LOOPS BACK:
       After GAME OVER display and score, waits for any keypress,
       resets all game-state POKEs, then GOTO 64 to restart.
       ESC still exits cleanly.

Output:
    Dev/defender/PreRelease/DefDat1.BAS — BASIC source
    Dev/defender/PreRelease/DefDat1.HBA — tokenised binary

Usage:
    python Dev/defender/gen_defdat1.py
"""

import sys
import subprocess
from pathlib import Path

# Import MC builder and constants from gen_defend11 (in Dev/defender/Iterations/)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Dev" / "defender" / "Iterations"))
from gen_defend11 import (
    build_routine, PARAM_BASE, EVENT_CODE_OFFSET,
    FRAME_DELAY, INITIAL_LIVES,
    HEART_FULL
)

OUT_BAS = Path("Progs/DefendERR/DefDat1.BAS")
OUT_HBA = Path("HBA/DEFDAT1.HBA")

# Game initial state constants (must match gen_defend11.py)
START_ROW   = 28
SHIP_SPRITE  = [0x01, 0x07, 0x1F, 0xFF, 0xFF, 0x1F, 0x07, 0x01]
ENEMY_SPRITE = [0x1C, 0xA0, 0x3E, 0xF1, 0xF1, 0x3E, 0xA0, 0x1C]


def main():
    asm = build_routine()
    mc_bytes = asm.bytes()
    mc_len = len(mc_bytes)
    patch_offsets = asm.abs_patches

    print(f"MC routine: {mc_len} bytes  ({len(patch_offsets)} patches)")

    n = mc_len if mc_len % 2 == 0 else mc_len + 1
    dim_d = (n // 2) - 1
    pb = PARAM_BASE
    delay = FRAME_DELAY

    out = []
    out.append("1 REM DefDat1 - Defender game (Prerelease)")
    out.append("2 REM A/a=up Z/z=down SPACE=fire ESC=exit")
    out.append("3 REM Chained from Defend splash screen")
    out.append("4 REM By kayto April 2026")
    # *** NO SCREEN 1 here — splash image stays visible during load ***
    out.append("5 CUROFF")

    out.append(f"6 DIM MC$({dim_d},1)")
    out.append("7 AD=VARPTR(MC$)-1")

    out.append(f"8 FOR I=0 TO {mc_len - 1}:READ V:POKE AD+I,V:NEXT I")
    out.append(f"9 FOR I=0 TO {len(patch_offsets) - 1}:READ P")
    out.append("10 L=PEEK(AD+P):H=PEEK(AD+P+1):W=L+H*256+AD")
    out.append("11 POKE AD+P,W-INT(W/256)*256:POKE AD+P+1,INT(W/256):NEXT I")

    # Param init
    out.append(f"15 POKE {pb},{START_ROW}")
    out.append(f"16 POKE {pb+1},{START_ROW}")
    for i, v in enumerate(SHIP_SPRITE):
        out.append(f"{17+i} POKE {pb+2+i},{v}")
    out.append(f"25 POKE {pb+10},{delay & 0xFF}")
    out.append(f"26 POKE {pb+11},{(delay >> 8) & 0xFF}")
    out.append(f"27 POKE {pb+12},27:POKE {pb+13},10")
    out.append(f"28 POKE {pb+14},12:POKE {pb+15},42")
    out.append(f"29 POKE {pb+16},21:POKE {pb+17},26")
    out.append(f"30 POKE {pb+18},37")
    out.append(f"31 POKE {pb+19},0")
    out.append(f"32 POKE {pb+20},0")
    out.append(f"33 POKE {pb+21},0")
    out.append(f"34 POKE {pb+22},0")
    out.append(f"35 POKE {pb+23},0")
    out.append(f"36 POKE {pb+24},0")
    out.append(f"37 POKE {pb+25},0")
    out.append(f"38 POKE {pb+34},1")
    for i, v in enumerate(ENEMY_SPRITE):
        out.append(f"{39+i} POKE {pb+26+i},{v}")
    out.append(f"47 POKE {pb+35},0")
    out.append(f"48 POKE {pb+36},0")
    out.append(f"49 POKE {pb+37},0")
    out.append(f"50 POKE {pb+38},0")
    out.append(f"51 POKE {pb+39},1")
    out.append(f"52 POKE {pb+40},0")
    out.append(f"53 POKE {pb+41},0")
    out.append(f"54 POKE {pb+42},{INITIAL_LIVES}")
    out.append(f"55 POKE {pb+43},0:POKE {pb+EVENT_CODE_OFFSET},0")
    for i, v in enumerate(HEART_FULL):
        out.append(f"{56+i} POKE {pb+44+i},{v}")

    # Pickup sound then SCREEN 1 — clears splash and signals game start
    out.append("64 SOUND 121,75:SOUND 95,75:SOUND 80,75:SOUND 59,110:SCREEN 1:DEFSEG=0:P=ARG(0)")
    out.append(f"65 Z=CALL(AD)")
    out.append(f"66 IF PEEK({pb+43})=1 THEN GOTO 80")
    out.append(f"67 EV=PEEK({pb+EVENT_CODE_OFFSET}):IF EV=0 THEN GOTO 100")
    out.append(f"68 POKE {pb+EVENT_CODE_OFFSET},0:ON EV GOSUB 200,210:GOTO 65")

    # Death path
    out.append(f"80 EV=PEEK({pb+EVENT_CODE_OFFSET}):POKE {pb+EVENT_CODE_OFFSET},0:POKE {pb+43},0")
    out.append(f"81 IF EV=3 THEN GOSUB 220")
    out.append(f"82 LV=PEEK({pb+42})-1:POKE {pb+42},LV")
    out.append(f"83 IF LV>0 THEN GOTO 65")

    # Game over — death sound, show score, prompt, wait for key, reset and loop back
    out.append(f"84 FOR I=50 TO 350 STEP 10:SOUND I,15:NEXT I")
    out.append(f"85 SCREEN 0:PRINT CHR$(1);:CURON")
    out.append(f"86 PRINT \"GAME OVER\":PRINT \"SCORE:\";PEEK({pb+40})")
    out.append(f"87 PRINT \"PRESS ANY KEY\"")
    out.append(f"88 K$=INKEY$:IF K$=\"\" THEN 88")
    # Reset gameplay state: ship pos, shot, enemies, score, wave, lives, dead, event
    out.append(f"89 POKE {pb},{START_ROW}:POKE {pb+1},{START_ROW}:POKE {pb+21},0:POKE {pb+24},0:POKE {pb+37},0")
    out.append(f"90 POKE {pb+40},0:POKE {pb+41},0:POKE {pb+42},{INITIAL_LIVES}:POKE {pb+43},0:POKE {pb+EVENT_CODE_OFFSET},0")
    out.append(f"91 GOTO 64")

    # Clean ESC exit
    out.append(f"100 SCREEN 0:PRINT CHR$(1);:CURON:END")

    # Sound routines
    out.append("200 FOR I=40 TO 80 STEP 8:SOUND I,3:NEXT I:RETURN")
    out.append("210 FOR I=50 TO 10 STEP -10:SOUND I,2:NEXT I:RETURN")
    out.append("220 FOR I=80 TO 20 STEP -10:SOUND I,5:NEXT I:RETURN")

    # MC data
    ln = 900
    per_line = 15
    for i in range(0, len(mc_bytes), per_line):
        chunk = mc_bytes[i:i+per_line]
        out.append(f"{ln} DATA {','.join(str(b) for b in chunk)}")
        ln += 1

    patch_per_line = 16
    for i in range(0, len(patch_offsets), patch_per_line):
        chunk = patch_offsets[i:i+patch_per_line]
        out.append(f"{ln} DATA {','.join(str(p) for p in chunk)}")
        ln += 1

    OUT_HBA.parent.mkdir(parents=True, exist_ok=True)
    OUT_BAS.write_text("\n".join(out) + "\n")
    print(f"Wrote {OUT_BAS} ({len(out)} lines)")

    result = subprocess.run(
        [sys.executable, "HBA_Format/hba_tokenize.py",
         str(OUT_BAS), str(OUT_HBA)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("Tokenizer error:", result.stderr)
    else:
        print(result.stdout.strip())


if __name__ == "__main__":
    main()
