#!/usr/bin/env python3
"""gen_ponggame.py - Generate PONGGAME.BAS with ball, solid net, left paddle + bounce.
Based on PONG7 development iteration (see Dev/pong/PONG_DEV.md).
By Kayto April 2026
Licensed under the MIT License. See LICENSE file for details.

Based on PONG6 with paddle-ball collision:
  - Ball bounces off paddle when overlapping
  - Ball passes through if no paddle overlap (miss)
  - Beep on miss (ball hits left wall)
  - Wall bounce still active at col 0 and 29

Memory strategy (DIM/VARPTR method from manual section 4.8.6):
  - MC code stored in DIM MC$(D,1) string array in BASIC RAM
  - Runtime address via AD=VARPTR(MC$)-1
  - Internal CALL/JP targets patched at runtime by BASIC
  - Parameters at fixed F605H user area (12 bytes, within 80-byte limit)

Param block at PARAM_BASE (F605H / 62981):
    +0     : col (byte column, 0-29)
    +1     : row (pixel row, 0-60)
    +2     : dx  (direction: 1 or 0xFF = -1)
    +3     : dy  (direction: 1 or 0xFF = -1)
    +4..+7 : 4 sprite pattern bytes
    +8,+9  : delay counter (little-endian word)
    +10    : py  (paddle Y position, pixel row, 0-52)
    +11    : old_py (previous py, written by MC)

Usage:
    python Progs/pong/gen_ponggame.py
"""

from pathlib import Path
import subprocess
import sys

PARAM_BASE = 62981    # F605H - fixed user area for params (12 bytes)

# === USER PREFERENCES (tweak these to taste) ===
BALL_DELAY = 10000   # frame delay counter (higher = slower ball)
PADDLE_SPEED = 4     # pixels per keypress (paddle movement step)
PADDLE_HEIGHT = 12   # paddle height in pixel rows
PADDLE_COL = 1       # left paddle column (gap to left wall)

# === SCREEN / HARDWARE CONSTANTS ===
MAX_COL = 29       # 30 columns (0-29)
MAX_ROW = 60       # 64 rows - 4 sprite height = 60
NET_COL = 15       # centre column for net
NET_BYTE = 0x18    # centre 2 bits set
PADDLE_BYTE = 0xFF # full byte = 8 pixels wide
MAX_PADDLE_Y = 52  # 64 - PADDLE_HEIGHT

# Key codes (lowercase for case-insensitive compare after OR 0x20)
KEY_A = 0x61       # 'a' (matches A/a after OR 0x20)
KEY_Z = 0x7A       # 'z' (matches Z/z after OR 0x20)
KEY_ESC = 0x1B     # ESC


class Asm:
    """Minimal Z80 assembler with label support and patch tracking.

    Assembled with base=0. Internal absolute references are tracked
    in self.abs_patches for runtime fixup by BASIC.
    """

    def __init__(self):
        self.code = []
        self.labels = {}
        self.patches = []       # (offset, label, type) for resolve
        self.abs_patches = []   # offsets needing runtime base addition

    def label(self, name):
        self.labels[name] = len(self.code)

    def emit(self, *bytes_):
        for b in bytes_:
            self.code.append(b & 0xFF)

    def emit_jr_cc(self, cc_byte, label):
        self.patches.append((len(self.code) + 1, label, 'jr'))
        self.emit(cc_byte, 0x00)

    def emit_call(self, label):
        off = len(self.code) + 1
        self.patches.append((off, label, 'abs'))
        self.abs_patches.append(off)
        self.emit(0xCD, 0x00, 0x00)

    def emit_jp(self, label):
        """Unconditional JP to label."""
        off = len(self.code) + 1
        self.patches.append((off, label, 'abs'))
        self.abs_patches.append(off)
        self.emit(0xC3, 0x00, 0x00)

    def emit_djnz(self, label):
        self.patches.append((len(self.code) + 1, label, 'jr'))
        self.emit(0x10, 0x00)

    def resolve(self):
        """Resolve with base=0. Absolute refs get offset-from-start values."""
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
                self.code[offset] = target & 0xFF
                self.code[offset + 1] = (target >> 8) & 0xFF

    def size(self):
        return len(self.code)

    def bytes(self):
        return list(self.code)


def lo(addr):
    return addr & 0xFF

def hi(addr):
    return (addr >> 8) & 0xFF


def build_routine():
    """Build MC: ball + solid net + left paddle with collision.

    Params at fixed PARAM_BASE (F605H).
    Code assembled with base=0, patched at runtime.

    Flow:
      1. Initial paddle draw (full, once)
      2. Main loop:
         a. Save py -> old_py
         b. Check key, update py (A/Z/ESC, case-insensitive)
         c. Erase ball (restore net if at NET_COL)
         d. If ball was at paddle col: redraw full paddle
         e. Differential paddle update (only changed rows)
         f. Update ball col/row with wall bounce
         g. Paddle collision check (bounce if overlap)
         h. Draw ball
         i. Delay -> loop
    """
    a = Asm()
    pb = PARAM_BASE

    # ==================== INITIAL PADDLE DRAW ====================
    a.emit(0x3A, lo(pb+10), hi(pb+10))  # LD A,(py)
    a.emit(0x0E, PADDLE_COL)            # LD C,PADDLE_COL
    a.emit_call('calc_vram')             # DE = VRAM addr
    a.emit(0x06, PADDLE_HEIGHT)          # LD B,12
    a.emit_call('draw_rows')             # draw full paddle
    # falls through to main_loop

    # ==================== MAIN LOOP ====================
    a.label('main_loop')

    # --- Save old_py ---
    a.emit(0x3A, lo(pb+10), hi(pb+10))  # LD A,(py)
    a.emit(0x32, lo(pb+11), hi(pb+11))  # LD (old_py),A

    # --- CHECK KEY (BDOS fn 11, non-blocking) ---
    a.emit(0x0E, 0x0B)                   # LD C,0x0B
    a.emit(0xCD, 0x05, 0x00)             # CALL 5 (BDOS)
    a.emit(0xA7)                         # AND A
    a.emit_jr_cc(0x28, 'no_key')         # JR Z

    # --- READ KEY (BDOS fn 6) ---
    a.emit(0x0E, 0x06)                   # LD C,6
    a.emit(0x1E, 0xFF)                   # LD E,0xFF
    a.emit(0xCD, 0x05, 0x00)             # CALL 5 (BDOS)

    # --- CHECK ESC ---
    a.emit(0xFE, KEY_ESC)               # CP ESC
    a.emit_jr_cc(0x20, 'not_esc')        # JR NZ
    a.emit(0xC9)                         # RET

    a.label('not_esc')
    # --- Case-insensitive: OR 0x20 forces lowercase ---
    a.emit(0xF6, 0x20)                   # OR 0x20
    a.emit(0xFE, KEY_A)                  # CP 'a'
    a.emit_jr_cc(0x28, 'paddle_up')      # JR Z
    a.emit(0xFE, KEY_Z)                  # CP 'z'
    a.emit_jr_cc(0x28, 'paddle_down')    # JR Z
    a.emit_jr_cc(0x18, 'no_key')         # JR

    a.label('paddle_up')
    a.emit(0x3A, lo(pb+10), hi(pb+10))  # LD A,(py)
    a.emit(0xD6, PADDLE_SPEED)           # SUB 2
    a.emit_jr_cc(0x30, 'paddle_store')   # JR NC
    a.emit(0xAF)                         # XOR A  ; clamp to 0
    a.emit_jr_cc(0x18, 'paddle_store')   # JR

    a.label('paddle_down')
    a.emit(0x3A, lo(pb+10), hi(pb+10))  # LD A,(py)
    a.emit(0xC6, PADDLE_SPEED)           # ADD A,2
    a.emit(0xFE, MAX_PADDLE_Y + 1)       # CP 53
    a.emit_jr_cc(0x38, 'paddle_store')   # JR C
    a.emit(0x3E, MAX_PADDLE_Y)           # LD A,52  ; clamp

    a.label('paddle_store')
    a.emit(0x32, lo(pb+10), hi(pb+10))  # LD (py),A

    a.label('no_key')

    # --- ERASE BALL at current (col, row) ---
    a.emit(0x3A, lo(pb+1), hi(pb+1))    # LD A,(row)
    a.emit(0x4F)                         # LD C,A
    a.emit(0x3A, lo(pb), hi(pb))         # LD A,(col)
    a.emit(0x47)                         # LD B,A  ; save col
    a.emit(0x79)                         # LD A,C  ; A = row
    a.emit(0x48)                         # LD C,B  ; C = col
    a.emit_call('calc_vram')             # DE = VRAM addr
    a.emit(0x06, 0x04)                   # LD B,4

    a.label('erase_ball_loop')
    a.emit(0xC5)                         # PUSH BC
    a.emit_call('set_cursor')
    a.emit(0x79)                         # LD A,C  ; col
    a.emit(0xFE, NET_COL)               # CP NET_COL
    a.emit_jr_cc(0x20, 'erase_ball_zero') # JR NZ
    a.emit(0x3E, NET_BYTE)              # LD A,NET_BYTE
    a.emit_jr_cc(0x18, 'erase_ball_write') # JR
    a.label('erase_ball_zero')
    a.emit(0xAF)                         # XOR A
    a.label('erase_ball_write')
    a.emit_call('write_byte')
    a.emit_call('next_row')              # DE += 30
    a.emit(0xC1)                         # POP BC
    a.emit_djnz('erase_ball_loop')

    # --- PADDLE FIX: if ball was at paddle col, redraw full paddle ---
    a.emit(0x3A, lo(pb), hi(pb))         # LD A,(col) - old ball col
    a.emit(0xFE, PADDLE_COL)            # CP PADDLE_COL
    a.emit_jr_cc(0x20, 'no_paddle_fix')  # JR NZ, skip
    # Redraw full paddle at current py
    a.emit(0x3A, lo(pb+10), hi(pb+10))  # LD A,(py)
    a.emit(0x0E, PADDLE_COL)            # LD C,PADDLE_COL
    a.emit_call('calc_vram')
    a.emit(0x06, PADDLE_HEIGHT)          # LD B,12
    a.emit_call('draw_rows')
    a.label('no_paddle_fix')

    # --- DIFFERENTIAL PADDLE UPDATE ---
    a.emit(0x3A, lo(pb+11), hi(pb+11))  # LD A,(old_py)
    a.emit(0x47)                         # LD B,A  ; B = old_py
    a.emit(0x3A, lo(pb+10), hi(pb+10))  # LD A,(py)
    a.emit(0xB8)                         # CP B
    a.emit_jr_cc(0x28, 'skip_paddle')    # JR Z, no movement
    a.emit_jr_cc(0x38, 'moved_up')       # JR C, new < old = moved up

    # --- Moved Down: erase top rows of old, draw bottom rows of new ---
    a.emit(0x78)                         # LD A,B  ; old_py
    a.emit(0x0E, PADDLE_COL)            # LD C,PADDLE_COL
    a.emit_call('calc_vram')
    a.emit(0x06, PADDLE_SPEED)           # LD B,2
    a.emit_call('erase_rows')
    a.emit(0x3A, lo(pb+10), hi(pb+10))  # LD A,(py)
    a.emit(0xC6, PADDLE_HEIGHT - PADDLE_SPEED) # ADD A,10
    a.emit(0x0E, PADDLE_COL)            # LD C,PADDLE_COL
    a.emit_call('calc_vram')
    a.emit(0x06, PADDLE_SPEED)           # LD B,2
    a.emit_call('draw_rows')
    a.emit_jr_cc(0x18, 'skip_paddle')    # JR

    # --- Moved Up: erase bottom rows of old, draw top rows of new ---
    a.label('moved_up')
    a.emit(0x78)                         # LD A,B  ; old_py
    a.emit(0xC6, PADDLE_HEIGHT - PADDLE_SPEED) # ADD A,10
    a.emit(0x0E, PADDLE_COL)            # LD C,PADDLE_COL
    a.emit_call('calc_vram')
    a.emit(0x06, PADDLE_SPEED)           # LD B,2
    a.emit_call('erase_rows')
    a.emit(0x3A, lo(pb+10), hi(pb+10))  # LD A,(py)
    a.emit(0x0E, PADDLE_COL)            # LD C,PADDLE_COL
    a.emit_call('calc_vram')
    a.emit(0x06, PADDLE_SPEED)           # LD B,2
    a.emit_call('draw_rows')

    a.label('skip_paddle')

    # --- UPDATE col: unified wall bounce (range 0-29) ---
    a.emit(0x3A, lo(pb), hi(pb))         # LD A,(col)
    a.emit(0x47)                         # LD B,A
    a.emit(0x3A, lo(pb+2), hi(pb+2))     # LD A,(dx)
    a.emit(0x80)                         # ADD A,B
    a.emit(0xFE, MAX_COL + 1)            # CP 30
    a.emit_jr_cc(0x38, 'col_ok')         # JR C
    a.emit(0x3A, lo(pb+2), hi(pb+2))     # LD A,(dx)
    a.emit(0xED, 0x44)                   # NEG
    a.emit(0x32, lo(pb+2), hi(pb+2))     # LD (dx),A
    a.emit(0x80)                         # ADD A,B
    a.label('col_ok')
    a.emit(0x32, lo(pb), hi(pb))         # LD (col),A

    # --- BEEP ON MISS: ball hit left wall (col 0 = passed paddle) ---
    a.emit(0xB7)                         # OR A  ; col == 0?
    a.emit_jr_cc(0x20, 'no_beep')        # JR NZ, skip beep
    a.emit(0x0E, 0x02)                   # LD C,2 (BDOS fn 2: console out)
    a.emit(0x1E, 0x07)                   # LD E,7 (BEL character)
    a.emit(0xCD, 0x05, 0x00)             # CALL 5 (BDOS)
    a.label('no_beep')

    # --- UPDATE row: bounce top/bottom ---
    a.emit(0x3A, lo(pb+1), hi(pb+1))     # LD A,(row)
    a.emit(0x47)                         # LD B,A
    a.emit(0x3A, lo(pb+3), hi(pb+3))     # LD A,(dy)
    a.emit(0x80)                         # ADD A,B
    a.emit(0xFE, MAX_ROW + 1)            # CP 61
    a.emit_jr_cc(0x38, 'row_ok')         # JR C
    a.emit(0x3A, lo(pb+3), hi(pb+3))     # LD A,(dy)
    a.emit(0xED, 0x44)                   # NEG
    a.emit(0x32, lo(pb+3), hi(pb+3))     # LD (dy),A
    a.emit(0x80)                         # ADD A,B
    a.label('row_ok')
    a.emit(0x32, lo(pb+1), hi(pb+1))     # LD (row),A

    # --- PADDLE COLLISION CHECK ---
    # If ball col == PADDLE_COL and dx == -1 (moving left)
    # and ball row overlaps paddle: bounce (reverse dx)
    a.emit(0x3A, lo(pb), hi(pb))         # LD A,(col)
    a.emit(0xFE, PADDLE_COL)            # CP PADDLE_COL
    a.emit_jr_cc(0x20, 'no_pbounce')     # JR NZ, no collision
    a.emit(0x3A, lo(pb+2), hi(pb+2))     # LD A,(dx)
    a.emit(0x3C)                         # INC A  ; 0xFF+1=0 → Z if moving left
    a.emit_jr_cc(0x20, 'no_pbounce')     # JR NZ, not moving left

    # Check vertical overlap: row+3 >= py AND row < py+PADDLE_HEIGHT
    a.emit(0x3A, lo(pb+10), hi(pb+10))  # LD A,(py)
    a.emit(0x47)                         # LD B,A  ; B = py
    a.emit(0x3A, lo(pb+1), hi(pb+1))     # LD A,(row)
    a.emit(0xC6, 0x03)                   # ADD A,3  ; A = row+3 (ball bottom)
    a.emit(0xB8)                         # CP B     ; (row+3) - py
    a.emit_jr_cc(0x38, 'no_pbounce')     # JR C, row+3 < py → ball above paddle

    a.emit(0x3A, lo(pb+10), hi(pb+10))  # LD A,(py)
    a.emit(0xC6, PADDLE_HEIGHT)          # ADD A,PADDLE_HEIGHT  ; A = py+12
    a.emit(0x47)                         # LD B,A  ; B = py+12
    a.emit(0x3A, lo(pb+1), hi(pb+1))     # LD A,(row)
    a.emit(0xB8)                         # CP B     ; row - (py+12)
    a.emit_jr_cc(0x30, 'no_pbounce')     # JR NC, row >= py+12 → ball below paddle

    # Collision! Reverse dx
    a.emit(0x3A, lo(pb+2), hi(pb+2))     # LD A,(dx)
    a.emit(0xED, 0x44)                   # NEG
    a.emit(0x32, lo(pb+2), hi(pb+2))     # LD (dx),A

    a.label('no_pbounce')

    # --- DRAW BALL at new (col, row) ---
    a.emit(0x3A, lo(pb), hi(pb))         # LD A,(col)
    a.emit(0x4F)                         # LD C,A
    a.emit(0x3A, lo(pb+1), hi(pb+1))     # LD A,(row)
    a.emit_call('calc_vram')             # DE = VRAM addr
    a.emit(0x21, lo(pb+4), hi(pb+4))     # HL = sprite data
    a.emit(0x06, 0x04)                   # LD B,4

    a.label('draw_ball_loop')
    a.emit(0xC5)                         # PUSH BC
    a.emit_call('set_cursor')
    a.emit(0x7E)                         # LD A,(HL)
    a.emit(0x23)                         # INC HL
    a.emit_call('write_byte')
    a.emit(0xE5)                         # PUSH HL
    a.emit_call('next_row')              # DE += 30
    a.emit(0xE1)                         # POP HL
    a.emit(0xC1)                         # POP BC
    a.emit_djnz('draw_ball_loop')

    # --- FRAME DELAY ---
    a.emit(0x2A, lo(pb+8), hi(pb+8))     # LD HL,(delay)
    a.label('delay_loop')
    a.emit(0x2B)                         # DEC HL
    a.emit(0x7C)                         # LD A,H
    a.emit(0xB5)                         # OR L
    a.emit_jr_cc(0x20, 'delay_loop')     # JR NZ

    # --- LOOP ---
    a.emit_jp('main_loop')               # JP main_loop

    # ==================== SUBROUTINES ====================

    # erase_rows: B = count, DE = VRAM start -> erase B rows of 0x00
    a.label('erase_rows')
    a.emit(0xC5)                         # PUSH BC
    a.emit_call('set_cursor')
    a.emit(0xAF)                         # XOR A
    a.emit_call('write_byte')
    a.emit_call('next_row')              # DE += 30
    a.emit(0xC1)                         # POP BC
    a.emit_djnz('erase_rows')
    a.emit(0xC9)                         # RET

    # draw_rows: B = count, DE = VRAM start -> draw B rows of 0xFF
    a.label('draw_rows')
    a.emit(0xC5)                         # PUSH BC
    a.emit_call('set_cursor')
    a.emit(0x3E, PADDLE_BYTE)           # LD A,0xFF
    a.emit_call('write_byte')
    a.emit_call('next_row')              # DE += 30
    a.emit(0xC1)                         # POP BC
    a.emit_djnz('draw_rows')
    a.emit(0xC9)                         # RET

    # next_row: advance DE by 30 (one LCD row)
    a.label('next_row')
    a.emit(0x62)                         # LD H,D
    a.emit(0x6B)                         # LD L,E
    a.emit(0x11, 0x1E, 0x00)             # LD DE,30
    a.emit(0x19)                         # ADD HL,DE
    a.emit(0xEB)                         # EX DE,HL
    a.emit(0xC9)                         # RET

    # calc_vram: A = row, C = col -> DE = row*30 + col
    a.label('calc_vram')
    a.emit(0x6F)                         # LD L,A
    a.emit(0x26, 0x00)                   # LD H,0
    a.emit(0x29)                         # ADD HL,HL    ; row*2
    a.emit(0xE5)                         # PUSH HL
    a.emit(0x29)                         # ADD HL,HL    ; row*4
    a.emit(0x29)                         # ADD HL,HL    ; row*8
    a.emit(0x29)                         # ADD HL,HL    ; row*16
    a.emit(0x29)                         # ADD HL,HL    ; row*32
    a.emit(0xD1)                         # POP DE       ; DE = row*2
    a.emit(0xB7)                         # OR A
    a.emit(0xED, 0x52)                   # SBC HL,DE   ; row*30
    a.emit(0x59)                         # LD E,C
    a.emit(0x16, 0x00)                   # LD D,0
    a.emit(0x19)                         # ADD HL,DE
    a.emit(0xEB)                         # EX DE,HL
    a.emit(0xC9)                         # RET

    # set_cursor: DE = VRAM addr -> set HD61830 cursor
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
    return a


def main():
    asm = build_routine()
    mc_bytes = asm.bytes()
    mc_len = len(mc_bytes)
    patch_offsets = asm.abs_patches

    print(f"MC routine: {mc_len} bytes (position-independent with patches)")
    print(f"Params at 0x{PARAM_BASE:04X} ({PARAM_BASE}), 12 bytes used")
    print(f"Patch offsets ({len(patch_offsets)}): {patch_offsets}")

    # DIM size: D = (N/2) - 1, N must be even
    n = mc_len if mc_len % 2 == 0 else mc_len + 1
    dim_d = (n // 2) - 1

    sprite = [0x18, 0x3C, 0x3C, 0x18]
    delay = BALL_DELAY
    start_col = 14
    start_row = 30
    start_dx = 1
    start_dy = 1
    start_py = 26   # centred for 12px paddle: (64-12)/2

    NET_PX1 = 123
    NET_PX2 = 124

    # Build BASIC
    out = []
    out.append("1 REM PONGGAME - based on dev PONG7")
    out.append("2 REM A/a=up Z/z=down ESC=exit")
    out.append("3 REM Ball 4x4, paddle 12px at col 1")
    out.append("4 REM By kayto April 2026")
    out.append("5 CUROFF:SCREEN 1")

    # DIM array and get address
    out.append(f"6 DIM MC$({dim_d},1)")
    out.append("7 AD=VARPTR(MC$)-1")

    # POKE MC bytes
    out.append(f"8 FOR I=0 TO {mc_len - 1}:READ V:POKE AD+I,V:NEXT I")

    # Patch absolute addresses: add AD to each 16-bit word at patch offset
    out.append(f"9 FOR I=0 TO {len(patch_offsets) - 1}:READ P")
    out.append("10 L=PEEK(AD+P):H=PEEK(AD+P+1):W=L+H*256+AD")
    out.append("11 POKE AD+P,W-INT(W/256)*256:POKE AD+P+1,INT(W/256):NEXT I")

    # Params at PARAM_BASE
    out.append(f"14 POKE {PARAM_BASE},{start_col}")
    out.append(f"15 POKE {PARAM_BASE+1},{start_row}")
    out.append(f"16 POKE {PARAM_BASE+2},{start_dx}")
    out.append(f"17 POKE {PARAM_BASE+3},{start_dy}")
    for i, v in enumerate(sprite):
        out.append(f"{18+i} POKE {PARAM_BASE+4+i},{v}")
    out.append(f"22 POKE {PARAM_BASE+8},{delay & 0xFF}")
    out.append(f"23 POKE {PARAM_BASE+9},{(delay >> 8) & 0xFF}")
    out.append(f"24 POKE {PARAM_BASE+10},{start_py}")

    # Draw solid net
    out.append("26 FOR R=0 TO 63")
    out.append(f"27 PSET({NET_PX1},R):PSET({NET_PX2},R):NEXT R")

    # Run MC (initial paddle drawn by MC prologue)
    out.append("30 DEFSEG=0:P=ARG(0):Z=CALL(AD)")
    out.append("40 SCREEN 0:PRINT CHR$(1);:CURON:END")

    # MC DATA lines (no trailing padding)
    ln = 900
    per_line = 15
    for i in range(0, len(mc_bytes), per_line):
        chunk = mc_bytes[i:i+per_line]
        out.append(f"{ln} DATA {','.join(str(b) for b in chunk)}")
        ln += 1

    # Patch offset DATA
    out.append(f"{ln} DATA {','.join(str(p) for p in patch_offsets)}")

    bas_path = Path("Progs/pong/PONGGAME.BAS")
    bas_path.write_text("\n".join(out) + "\n")
    print(f"\nWrote {bas_path} ({len(out)} lines)")

    # Tokenize
    result = subprocess.run(
        [sys.executable, "HBA_Format/hba_tokenize.py", str(bas_path), "Progs/pong/PONGGAME.HBA"],
        capture_output=True, text=True
    )
    print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())


if __name__ == "__main__":
    main()
