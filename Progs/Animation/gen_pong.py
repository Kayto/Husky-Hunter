#!/usr/bin/env python3
"""gen_pong.py - Generate PONG.BAS with bouncing ball mechanics.
By Kayto 14/04/2026
Licensed under the MIT License. See LICENSE file for details.

Pong-style ball mechanics for the Husky Hunter LCD.
A small 4x4 ball bounces off all four screen edges.
Ball moves diagonally (1 byte-column and 1 pixel-row per frame).

BASIC loads MC + params into RAM, then single CALL.
The entire animation loop runs in MC.

Memory layout:
  ROUTINE_BASE (F605H / 62981): MC code
  PARAM_BASE   (F740H / 63296): parameter block
    +0     : col (byte column, 0-29)
    +1     : row (pixel row, 0-60)
    +2     : dx  (direction: 1 or 0xFF = -1)
    +3     : dy  (direction: 1 or 0xFF = -1)
    +4..+7 : 4 sprite pattern bytes
    +8,+9  : delay counter (little-endian word)

Usage:
    python Dev/gen_pong.py
"""

from pathlib import Path
import subprocess
import sys

ROUTINE_BASE = 62981  # F605H
PARAM_BASE = 63296    # F740H

# Screen bounds
MAX_COL = 29   # 30 columns (0-29)
MAX_ROW = 60   # 64 rows - 4 sprite height = 60


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


def build_routine():
    """Build MC pong ball mechanics.

    Flow: erase at (col,row) -> update col with bounce -> update row
          with bounce -> draw at (col,row) -> delay -> key check -> loop

    calc_vram: A=row, C=col -> DE = row*30 + col
    Bounce: when col or row goes out of bounds, negate dx/dy (NEG)
            and recompute with reversed direction.
    """
    a = Asm(ROUTINE_BASE)
    pb = PARAM_BASE

    # ==================== MAIN LOOP ====================
    a.label('main_loop')

    # --- ERASE at current (col, row) ---
    a.emit(0x3A, lo(pb+1), hi(pb+1))    # LD A,(row)
    a.emit(0x4F)                         # LD C,A  ; C = row temporarily
    a.emit(0x3A, lo(pb), hi(pb))         # LD A,(col)
    a.emit(0x47)                         # LD B,A  ; save col in B
    a.emit(0x79)                         # LD A,C  ; A = row
    a.emit(0x48)                         # LD C,B  ; C = col
    a.emit_call('calc_vram')             # DE = VRAM addr
    a.emit(0x06, 0x04)                   # LD B,4

    a.label('erase_loop')
    a.emit(0xC5)                         # PUSH BC
    a.emit_call('set_cursor')
    a.emit(0xAF)                         # XOR A
    a.emit_call('write_byte')
    a.emit(0x62)                         # LD H,D
    a.emit(0x6B)                         # LD L,E
    a.emit(0x01, 0x1E, 0x00)             # LD BC,30
    a.emit(0x09)                         # ADD HL,BC
    a.emit(0xEB)                         # EX DE,HL
    a.emit(0xC1)                         # POP BC
    a.emit_djnz('erase_loop')

    # --- UPDATE col: col += dx, bounce off left/right ---
    a.emit(0x3A, lo(pb), hi(pb))         # LD A,(col)
    a.emit(0x47)                         # LD B,A    ; B = old col
    a.emit(0x3A, lo(pb+2), hi(pb+2))     # LD A,(dx)
    a.emit(0x80)                         # ADD A,B   ; A = col + dx
    a.emit(0xFE, MAX_COL + 1)            # CP 30     ; unsigned: 0-29 ok
    a.emit_jr_cc(0x38, 'col_ok')         # JR C,col_ok
    # Out of bounds: negate dx, recompute
    a.emit(0x3A, lo(pb+2), hi(pb+2))     # LD A,(dx)
    a.emit(0xED, 0x44)                   # NEG       ; negate direction
    a.emit(0x32, lo(pb+2), hi(pb+2))     # LD (dx),A
    a.emit(0x80)                         # ADD A,B   ; col = old + new dx
    a.label('col_ok')
    a.emit(0x32, lo(pb), hi(pb))         # LD (col),A

    # --- UPDATE row: row += dy, bounce off top/bottom ---
    a.emit(0x3A, lo(pb+1), hi(pb+1))     # LD A,(row)
    a.emit(0x47)                         # LD B,A    ; B = old row
    a.emit(0x3A, lo(pb+3), hi(pb+3))     # LD A,(dy)
    a.emit(0x80)                         # ADD A,B   ; A = row + dy
    a.emit(0xFE, MAX_ROW + 1)            # CP 61     ; unsigned: 0-60 ok
    a.emit_jr_cc(0x38, 'row_ok')         # JR C,row_ok
    # Out of bounds: negate dy, recompute
    a.emit(0x3A, lo(pb+3), hi(pb+3))     # LD A,(dy)
    a.emit(0xED, 0x44)                   # NEG
    a.emit(0x32, lo(pb+3), hi(pb+3))     # LD (dy),A
    a.emit(0x80)                         # ADD A,B   ; row = old + new dy
    a.label('row_ok')
    a.emit(0x32, lo(pb+1), hi(pb+1))     # LD (row),A

    # --- DRAW at new (col, row) ---
    # Load row and col for calc_vram
    a.emit(0x3A, lo(pb), hi(pb))         # LD A,(col)
    a.emit(0x4F)                         # LD C,A    ; C = col
    a.emit(0x3A, lo(pb+1), hi(pb+1))     # LD A,(row)
    # A = row, C = col
    a.emit_call('calc_vram')             # DE = VRAM addr
    a.emit(0x21, lo(pb+4), hi(pb+4))     # HL = sprite data (PARAM+4)
    a.emit(0x06, 0x04)                   # LD B,4

    a.label('draw_loop')
    a.emit(0xC5)                         # PUSH BC
    a.emit_call('set_cursor')
    a.emit(0x7E)                         # LD A,(HL)
    a.emit(0x23)                         # INC HL
    a.emit_call('write_byte')
    a.emit(0xEB)                         # EX DE,HL
    a.emit(0x01, 0x1E, 0x00)             # LD BC,30
    a.emit(0x09)                         # ADD HL,BC
    a.emit(0xEB)                         # EX DE,HL
    a.emit(0xC1)                         # POP BC
    a.emit_djnz('draw_loop')

    # --- FRAME DELAY ---
    a.emit(0x2A, lo(pb+8), hi(pb+8))     # LD HL,(delay)
    a.label('delay_loop')
    a.emit(0x2B)                         # DEC HL
    a.emit(0x7C)                         # LD A,H
    a.emit(0xB5)                         # OR L
    a.emit_jr_cc(0x20, 'delay_loop')     # JR NZ

    # --- CHECK KEYPRESS (BDOS fn 11) ---
    a.emit(0x0E, 0x0B)                   # LD C,0x0B
    a.emit(0xCD, 0x05, 0x00)             # CALL 5
    a.emit(0xA7)                         # AND A
    a.emit_jp_cc(0xCA, 'main_loop')      # JP Z,main_loop

    a.emit(0xC9)                         # RET

    # ==================== SUBROUTINES ====================

    # calc_vram: compute VRAM address
    # Input:  A = row, C = col
    # Output: DE = row*30 + col
    # Clobbers: A, HL, DE.  Preserves: B, C
    a.label('calc_vram')
    a.emit(0x6F)                         # LD L,A
    a.emit(0x26, 0x00)                   # LD H,0       ; HL = row
    a.emit(0x29)                         # ADD HL,HL    ; row*2
    a.emit(0xE5)                         # PUSH HL      ; save row*2
    a.emit(0x29)                         # ADD HL,HL    ; row*4
    a.emit(0x29)                         # ADD HL,HL    ; row*8
    a.emit(0x29)                         # ADD HL,HL    ; row*16
    a.emit(0x29)                         # ADD HL,HL    ; row*32
    a.emit(0xD1)                         # POP DE       ; DE = row*2
    a.emit(0xB7)                         # OR A         ; clear carry
    a.emit(0xED, 0x52)                   # SBC HL,DE   ; HL = row*30
    a.emit(0x59)                         # LD E,C      ; E = col
    a.emit(0x16, 0x00)                   # LD D,0
    a.emit(0x19)                         # ADD HL,DE   ; HL = row*30 + col
    a.emit(0xEB)                         # EX DE,HL    ; DE = VRAM addr
    a.emit(0xC9)                         # RET

    # set_cursor: DE = VRAM addr -> set HD61830 cursor
    # Clobbers: A only
    a.label('set_cursor')
    a.emit_call('wait_busy')
    a.emit(0x3E, 0x0A)                   # LD A,0x0A
    a.emit(0xD3, 0x21)                   # OUT (0x21),A
    a.emit_call('wait_busy')
    a.emit(0x7B)                         # LD A,E
    a.emit(0xD3, 0x20)                   # OUT (0x20),A
    a.emit_call('wait_busy')
    a.emit(0x3E, 0x0B)                   # LD A,0x0B
    a.emit(0xD3, 0x21)                   # OUT (0x21),A
    a.emit_call('wait_busy')
    a.emit(0x7A)                         # LD A,D
    a.emit(0xD3, 0x20)                   # OUT (0x20),A
    a.emit(0xC9)                         # RET

    # write_byte: A = data -> write to HD61830 VRAM
    # Clobbers: A only
    a.label('write_byte')
    a.emit(0xF5)                         # PUSH AF
    a.emit_call('wait_busy')
    a.emit(0x3E, 0x0C)                   # LD A,0x0C
    a.emit(0xD3, 0x21)                   # OUT (0x21),A
    a.emit_call('wait_busy')
    a.emit(0xF1)                         # POP AF
    a.emit(0xD3, 0x20)                   # OUT (0x20),A
    a.emit(0xC9)                         # RET

    # wait_busy: poll HD61830 status
    a.label('wait_busy')
    a.emit(0xDB, 0x21)                   # IN A,(0x21)
    a.emit(0x07)                         # RLCA
    a.emit(0x38, 0xFB)                   # JR C,-5
    a.emit(0xC9)                         # RET

    a.resolve()
    return a.bytes()


def main():
    mc_bytes = build_routine()
    mc_len = len(mc_bytes)

    print(f"MC routine: {mc_len} bytes at 0x{ROUTINE_BASE:04X} ({ROUTINE_BASE})")
    print(f"Ends at 0x{ROUTINE_BASE + mc_len - 1:04X} ({ROUTINE_BASE + mc_len - 1})")
    print(f"Param block at 0x{PARAM_BASE:04X} ({PARAM_BASE})")

    if ROUTINE_BASE + mc_len > PARAM_BASE:
        print(f"ERROR: routine overflows into param block!")
        sys.exit(1)

    gap = PARAM_BASE - (ROUTINE_BASE + mc_len)
    print(f"Gap: {gap} bytes")

    # 4x4 ball sprite (rounded corners)
    sprite = [0x18, 0x3C, 0x3C, 0x18]
    delay = 2000          # faster than SPRITE demos for snappier feel
    start_col = 14        # centre of 30 columns
    start_row = 30        # centre of 64 rows
    start_dx = 1          # moving right
    start_dy = 1          # moving down

    # Build BASIC
    out = []
    out.append("1 REM PONG - Ball bounce mechanics")
    out.append("2 REM 4x4 ball bounces off all edges")
    out.append("3 REM Press any key to exit")
    out.append("4 REM By kayto April 2026")
    out.append("5 CUROFF:SCREEN 1")
    out.append(f"6 FOR I=0 TO {mc_len - 1}:READ V:POKE {ROUTINE_BASE}+I,V:NEXT I")
    out.append(f"10 POKE {PARAM_BASE},{start_col}")
    out.append(f"11 POKE {PARAM_BASE+1},{start_row}")
    out.append(f"12 POKE {PARAM_BASE+2},{start_dx}")
    out.append(f"13 POKE {PARAM_BASE+3},{start_dy}")
    for i, v in enumerate(sprite):
        out.append(f"{14+i} POKE {PARAM_BASE+4+i},{v}")
    out.append(f"18 POKE {PARAM_BASE+8},{delay & 0xFF}")
    out.append(f"19 POKE {PARAM_BASE+9},{(delay >> 8) & 0xFF}")
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

    bas_path = Path("Dev/PONG.BAS")
    bas_path.write_text("\n".join(out) + "\n")
    print(f"\nWrote {bas_path} ({len(out)} lines)")

    # Tokenize
    result = subprocess.run(
        [sys.executable, "HBA_Format/hba_tokenize.py", str(bas_path), "Dev/PONG.HBA"],
        capture_output=True, text=True
    )
    print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())


if __name__ == "__main__":
    main()
