#!/usr/bin/env python3
"""gen_bounce2.py - Generate BOUNCE2.BAS with two-sprite wave animation.
By Kayto 13/04/2026
Licensed under the MIT License. See LICENSE file for details.

Two sprites on the Husky Hunter LCD following the same sine wave
but moving in opposite directions — one left-to-right, one right-to-left.
They cross in the middle and pass through each other.

BASIC loads MC + params into RAM, then single CALL.
The entire animation loop runs in MC.

Memory layout:
  ROUTINE_BASE (F605H / 62981): MC code + embedded wave table
  PARAM_BASE   (F740H / 63296): parameter block
    +0      : col1 (sprite 1 column, moves right)
    +1      : col2 (sprite 2 column, moves left)
    +2..+9  : sprite1 data (8 bytes) - circle
    +10..+17: sprite2 data (8 bytes) - diamond
    +18,+19 : delay counter (little-endian word)

Usage:
    python gen_bounce2.py
"""

import math
from pathlib import Path
import subprocess
import sys

ROUTINE_BASE = 62981  # F605H
PARAM_BASE = 63296    # F740H

# Wave parameters
WAVE_CENTRE = 28
WAVE_AMPLITUDE = 20
WAVE_PERIOD = 30


class Asm:
    """Minimal Z80 assembler with label support."""

    def __init__(self, base_addr):
        self.base = base_addr
        self.code = []
        self.labels = {}
        self.patches = []

    def label(self, name):
        self.labels[name] = len(self.code)

    def emit(self, *bytes_):
        for b in bytes_:
            self.code.append(b & 0xFF)

    def emit_jr_cc(self, cc_byte, label):
        self.patches.append((len(self.code) + 1, label, 'jr'))
        self.emit(cc_byte, 0x00)

    def emit_call(self, label):
        self.patches.append((len(self.code) + 1, label, 'abs'))
        self.emit(0xCD, 0x00, 0x00)

    def emit_jp_cc(self, cc_byte, label):
        self.patches.append((len(self.code) + 1, label, 'abs'))
        self.emit(cc_byte, 0x00, 0x00)

    def emit_djnz(self, label):
        self.patches.append((len(self.code) + 1, label, 'jr'))
        self.emit(0x10, 0x00)

    def emit_ld_hl_nn(self, label):
        """LD HL,nn where nn is the absolute address of a label."""
        self.patches.append((len(self.code) + 1, label, 'abs'))
        self.emit(0x21, 0x00, 0x00)

    def resolve(self):
        for offset, label, ptype in self.patches:
            if label not in self.labels:
                raise ValueError(f"Undefined label: {label}")
            target = self.labels[label]
            if ptype == 'jr':
                disp = target - (offset + 1)
                if disp < -128 or disp > 127:
                    raise ValueError(f"JR out of range to {label}: {disp}")
                self.code[offset] = disp & 0xFF
            elif ptype == 'abs':
                addr = self.base + target
                self.code[offset] = addr & 0xFF
                self.code[offset + 1] = (addr >> 8) & 0xFF

    def bytes(self):
        return list(self.code)


def lo(addr):
    return addr & 0xFF

def hi(addr):
    return (addr >> 8) & 0xFF


def build_wave_table():
    """Build 30-entry sine wave table (one Y-row per column)."""
    wave = []
    for col in range(30):
        row = int(WAVE_CENTRE + WAVE_AMPLITUDE *
                  math.sin(col * 2 * math.pi / WAVE_PERIOD))
        row = max(0, min(56, row))
        wave.append(row)
    return wave


def build_routine():
    """Build MC two-sprite wave animation.

    Two sprites share the same wave table. Sprite 1 moves right
    (col1 increments, wraps at 30). Sprite 2 moves left (col2
    decrements, wraps at 0->29).

    Uses an erase_at subroutine for both erases (identical operation),
    and inline draw loops (different sprite data pointers).

    Flow per frame:
      erase sprite1 at old col1
      erase sprite2 at old col2
      update col1 (inc, wrap 30->0)
      update col2 (dec, wrap 0->29)
      draw sprite1 at new col1
      draw sprite2 at new col2
      delay -> key check -> loop
    """
    a = Asm(ROUTINE_BASE)
    pb = PARAM_BASE

    # ==================== MAIN LOOP ====================
    a.label('main_loop')

    # --- ERASE sprite 1 at old col1 ---
    a.emit(0x3A, lo(pb), hi(pb))        # LD A,(col1)
    a.emit_call('erase_at')

    # --- ERASE sprite 2 at old col2 ---
    a.emit(0x3A, lo(pb+1), hi(pb+1))    # LD A,(col2)
    a.emit_call('erase_at')

    # --- UPDATE col1: increment, wrap at 30 ---
    a.emit(0x3A, lo(pb), hi(pb))        # LD A,(col1)
    a.emit(0x3C)                        # INC A
    a.emit(0xFE, 30)                    # CP 30
    a.emit_jr_cc(0x38, 'no_wrap1')      # JR C,no_wrap1
    a.emit(0xAF)                        # XOR A
    a.label('no_wrap1')
    a.emit(0x32, lo(pb), hi(pb))        # LD (col1),A

    # --- UPDATE col2: decrement, wrap 0->29 ---
    a.emit(0x3A, lo(pb+1), hi(pb+1))    # LD A,(col2)
    a.emit(0xD6, 1)                     # SUB 1 (carry if was 0)
    a.emit_jr_cc(0x30, 'no_wrap2')      # JR NC,no_wrap2
    a.emit(0x3E, 29)                    # LD A,29
    a.label('no_wrap2')
    a.emit(0x32, lo(pb+1), hi(pb+1))    # LD (col2),A

    # --- DRAW sprite 1 at new col1 ---
    a.emit(0x3A, lo(pb), hi(pb))        # LD A,(col1)
    a.emit_call('calc_vram')            # DE = VRAM addr
    a.emit(0x21, lo(pb+2), hi(pb+2))    # HL = sprite1 data
    a.emit(0x06, 0x08)                  # LD B,8

    a.label('draw1_loop')
    a.emit(0xC5)                        # PUSH BC
    a.emit_call('set_cursor')
    a.emit(0x7E)                        # LD A,(HL)
    a.emit(0x23)                        # INC HL
    a.emit_call('write_byte')
    a.emit(0xEB)                        # EX DE,HL
    a.emit(0x01, 0x1E, 0x00)            # LD BC,30
    a.emit(0x09)                        # ADD HL,BC
    a.emit(0xEB)                        # EX DE,HL
    a.emit(0xC1)                        # POP BC
    a.emit_djnz('draw1_loop')

    # --- DRAW sprite 2 at new col2 ---
    a.emit(0x3A, lo(pb+1), hi(pb+1))    # LD A,(col2)
    a.emit_call('calc_vram')            # DE = VRAM addr
    a.emit(0x21, lo(pb+10), hi(pb+10))  # HL = sprite2 data
    a.emit(0x06, 0x08)                  # LD B,8

    a.label('draw2_loop')
    a.emit(0xC5)                        # PUSH BC
    a.emit_call('set_cursor')
    a.emit(0x7E)                        # LD A,(HL)
    a.emit(0x23)                        # INC HL
    a.emit_call('write_byte')
    a.emit(0xEB)                        # EX DE,HL
    a.emit(0x01, 0x1E, 0x00)            # LD BC,30
    a.emit(0x09)                        # ADD HL,BC
    a.emit(0xEB)                        # EX DE,HL
    a.emit(0xC1)                        # POP BC
    a.emit_djnz('draw2_loop')

    # --- FRAME DELAY ---
    a.emit(0x2A, lo(pb+18), hi(pb+18))  # LD HL,(delay)
    a.label('delay_loop')
    a.emit(0x2B)                        # DEC HL
    a.emit(0x7C)                        # LD A,H
    a.emit(0xB5)                        # OR L
    a.emit_jr_cc(0x20, 'delay_loop')    # JR NZ

    # --- CHECK KEYPRESS (BDOS fn 11) ---
    a.emit(0x0E, 0x0B)                  # LD C,0x0B
    a.emit(0xCD, 0x05, 0x00)            # CALL 5
    a.emit(0xA7)                        # AND A
    a.emit_jp_cc(0xCA, 'main_loop')     # JP Z,main_loop

    a.emit(0xC9)                        # RET

    # ==================== SUBROUTINES ====================

    # erase_at: erase 8 rows at column A on the wave
    # Input: A = column (0-29)
    # Clobbers: A, HL, DE, BC
    a.label('erase_at')
    a.emit_call('calc_vram')            # DE = VRAM addr
    a.emit(0x06, 0x08)                  # LD B,8
    a.label('erase_loop')
    a.emit(0xC5)                        # PUSH BC
    a.emit_call('set_cursor')
    a.emit(0xAF)                        # XOR A
    a.emit_call('write_byte')
    a.emit(0x62)                        # LD H,D
    a.emit(0x6B)                        # LD L,E
    a.emit(0x01, 0x1E, 0x00)            # LD BC,30
    a.emit(0x09)                        # ADD HL,BC
    a.emit(0xEB)                        # EX DE,HL
    a.emit(0xC1)                        # POP BC
    a.emit_djnz('erase_loop')
    a.emit(0xC9)                        # RET

    # calc_vram: compute VRAM address for a column using wave table
    # Input:  A = column (0-29)
    # Output: DE = VRAM address (wave_table[col]*30 + col)
    # Clobbers: A, HL, DE, C.  Preserves: B
    a.label('calc_vram')
    a.emit(0x4F)                        # LD C,A         ; save col
    a.emit(0x5F)                        # LD E,A
    a.emit(0x16, 0x00)                  # LD D,0
    a.emit_ld_hl_nn('wave_table')       # LD HL,wave_table
    a.emit(0x19)                        # ADD HL,DE      ; HL -> wave_table[col]
    a.emit(0x7E)                        # LD A,(HL)      ; A = row
    a.emit(0x6F)                        # LD L,A
    a.emit(0x26, 0x00)                  # LD H,0
    a.emit(0x29)                        # ADD HL,HL      ; row*2
    a.emit(0xE5)                        # PUSH HL        ; save row*2
    a.emit(0x29)                        # ADD HL,HL      ; row*4
    a.emit(0x29)                        # ADD HL,HL      ; row*8
    a.emit(0x29)                        # ADD HL,HL      ; row*16
    a.emit(0x29)                        # ADD HL,HL      ; row*32
    a.emit(0xD1)                        # POP DE         ; DE = row*2
    a.emit(0xB7)                        # OR A           ; clear carry
    a.emit(0xED, 0x52)                  # SBC HL,DE      ; HL = row*30
    a.emit(0x59)                        # LD E,C         ; E = col
    a.emit(0x16, 0x00)                  # LD D,0
    a.emit(0x19)                        # ADD HL,DE      ; HL = row*30 + col
    a.emit(0xEB)                        # EX DE,HL       ; DE = VRAM addr
    a.emit(0xC9)                        # RET

    # set_cursor: DE = VRAM addr -> set HD61830 cursor
    # Clobbers: A only
    a.label('set_cursor')
    a.emit_call('wait_busy')
    a.emit(0x3E, 0x0A)
    a.emit(0xD3, 0x21)
    a.emit_call('wait_busy')
    a.emit(0x7B)                        # LD A,E
    a.emit(0xD3, 0x20)
    a.emit_call('wait_busy')
    a.emit(0x3E, 0x0B)
    a.emit(0xD3, 0x21)
    a.emit_call('wait_busy')
    a.emit(0x7A)                        # LD A,D
    a.emit(0xD3, 0x20)
    a.emit(0xC9)

    # write_byte: A = data byte -> write to HD61830 VRAM
    # Clobbers: A only
    a.label('write_byte')
    a.emit(0xF5)                        # PUSH AF
    a.emit_call('wait_busy')
    a.emit(0x3E, 0x0C)
    a.emit(0xD3, 0x21)
    a.emit_call('wait_busy')
    a.emit(0xF1)                        # POP AF
    a.emit(0xD3, 0x20)
    a.emit(0xC9)

    # wait_busy: poll HD61830 status
    a.label('wait_busy')
    a.emit(0xDB, 0x21)                  # IN A,(0x21)
    a.emit(0x07)                        # RLCA
    a.emit(0x38, 0xFB)                  # JR C,-5
    a.emit(0xC9)

    # ==================== DATA ====================
    wave = build_wave_table()
    a.label('wave_table')
    for v in wave:
        a.emit(v)

    a.resolve()
    return a.bytes(), wave


def main():
    mc_bytes, wave = build_routine()
    mc_len = len(mc_bytes)

    print(f"MC routine: {mc_len} bytes at 0x{ROUTINE_BASE:04X} ({ROUTINE_BASE})")
    print(f"Ends at 0x{ROUTINE_BASE + mc_len - 1:04X} ({ROUTINE_BASE + mc_len - 1})")
    print(f"Param block at 0x{PARAM_BASE:04X} ({PARAM_BASE})")

    if ROUTINE_BASE + mc_len > PARAM_BASE:
        print(f"ERROR: routine overflows into param block!")
        sys.exit(1)

    gap = PARAM_BASE - (ROUTINE_BASE + mc_len)
    print(f"Gap: {gap} bytes")
    print(f"Wave table ({len(wave)} entries): {wave}")

    # Sprites
    sprite1 = [0x3C, 0x7E, 0xFF, 0xFF, 0xFF, 0xFF, 0x7E, 0x3C]  # circle
    sprite2 = [0x18, 0x3C, 0x7E, 0xFF, 0x7E, 0x3C, 0x18, 0x00]  # diamond
    delay = 4000
    start_col1 = 0   # left edge, moving right
    start_col2 = 15  # half-screen apart, moving left

    # Build BASIC
    out = []
    out.append("1 REM BOUNCE2 - Two-sprite wave animation")
    out.append("2 REM Circle moves right, diamond moves left")
    out.append("3 REM Press any key to exit")
    out.append("4 REM By kayto April 2026")
    out.append("5 CUROFF:SCREEN 1")
    out.append(f"6 FOR I=0 TO {mc_len - 1}:READ V:POKE {ROUTINE_BASE}+I,V:NEXT I")
    out.append(f"10 POKE {PARAM_BASE},{start_col1}")
    out.append(f"11 POKE {PARAM_BASE+1},{start_col2}")
    # sprite1 data at PARAM+2..+9
    for i, v in enumerate(sprite1):
        out.append(f"{12+i} POKE {PARAM_BASE+2+i},{v}")
    # sprite2 data at PARAM+10..+17
    for i, v in enumerate(sprite2):
        out.append(f"{20+i} POKE {PARAM_BASE+10+i},{v}")
    # delay at PARAM+18..+19
    out.append(f"28 POKE {PARAM_BASE+18},{delay & 0xFF}")
    out.append(f"29 POKE {PARAM_BASE+19},{(delay >> 8) & 0xFF}")
    out.append(f"30 P=ARG(0):Z=CALL({ROUTINE_BASE})")
    out.append("40 SCREEN 0:PRINT CHR$(1);:CURON:END")

    # MC DATA lines
    ln = 900
    per_line = 15
    for i in range(0, len(mc_bytes), per_line):
        chunk = mc_bytes[i:i+per_line]
        is_last = (i + per_line >= len(mc_bytes))
        suffix = ',0' if is_last else ''
        out.append(f"{ln} DATA {','.join(str(b) for b in chunk)}{suffix}")
        ln += 1

    bas_path = Path("Dev/Animation/BOUNCE2.BAS")
    bas_path.write_text("\n".join(out) + "\n")
    print(f"\nWrote {bas_path} ({len(out)} lines)")

    # Tokenize
    result = subprocess.run(
        [sys.executable, "HBA_Format/hba_tokenize.py", str(bas_path), "Dev/Animation/BOUNCE2.HBA"],
        capture_output=True, text=True
    )
    print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())


if __name__ == "__main__":
    main()
