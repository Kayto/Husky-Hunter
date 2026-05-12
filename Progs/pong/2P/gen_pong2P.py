#!/usr/bin/env python3
"""gen_pong2P.py - PONG2P: delta paddle rendering + conditional score draw.
By Kayto May 2026
Licensed under the MIT License. See LICENSE file for details.

Developed from PongMP iteration 3 (Dev/pongMP/gen_pongMP3.py) — dev scratch at Dev/pongMP/.
Dev/pongMP/ - extends pongMP2 with two LCD write optimisations:

  1. Delta paddle rendering:
     Only the rows that changed are written to the LCD each frame.
     Paddle moves PADDLE_SPEED rows per frame, so at most PADDLE_SPEED
     rows are erased and PADDLE_SPEED rows are drawn per paddle per frame
     (vs PADDLE_HEIGHT erase + PADDLE_HEIGHT draw in pongMP2).
     When the paddle hasn't moved, zero LCD writes occur for that paddle.
     Worst case (both paddles moving): 4*4 = 16 writes vs 96 in pongMP2.

  2. Conditional score draw:
     Scores are only redrawn when:
       a) score_dirty flag is set (a goal just occurred), OR
       b) ball_row < SCORE_ROWS (ball is overlapping the score area)
     This avoids 14 unnecessary LCD writes on most frames.
     score_dirty is initialised to 1 so scores appear on first frame.

Param block at PARAM_BASE (F605H / 62981), 18 bytes:
    +0..+16  same as pongMP2
    +17    : score_dirty  (1=redraw scores, 0=skip unless ball overlaps)

Usage:
    python Progs/pong/2P/gen_pong2P.py
"""

from pathlib import Path
import subprocess
import sys

PARAM_BASE = 62981    # F605H

# === USER PREFERENCES ===
BALL_DELAY       = 0       # frame delay; 0 = max speed (LCD is the bottleneck)
PADDLE_SPEED     = 4       # pixels per frame; also max delta rows drawn per move
PADDLE_HEIGHT    = 12

# Difficulty: 0=easy (paddle at walls), 1=medium, 2=hard (paddle near net)
# Paddles closer to the net = less gap for the ball to squeeze through before a miss
DIFFICULTY = 1
_PADDLE_COLS = {
    0: (1,  28),   # easy:   ball must reach col 0 or 29 before a miss
    1: (4,  25),   # medium: ~3 byte-columns of gap at each wall
    2: (7,  22),   # hard:   ~6 byte-columns of gap at each wall
}
PADDLE_COL, RIGHT_PADDLE_COL = _PADDLE_COLS[DIFFICULTY]

# === SCREEN / HARDWARE CONSTANTS ===
MAX_COL      = 29
MIN_ROW      = 1
MAX_ROW      = 60
NET_COL      = 15
NET_BYTE     = 0x18
PADDLE_BYTE  = 0xFF
MAX_PADDLE_Y = 52   # 64 - PADDLE_HEIGHT

P1_SCORE_COL = 7
P2_SCORE_COL = 22
SCORE_ROWS   = 7

DIGIT_FONT = [
    # 0
    0x7C, 0x44, 0x44, 0x44, 0x44, 0x44, 0x7C,
    # 1
    0x10, 0x18, 0x10, 0x10, 0x10, 0x10, 0x38,
    # 2
    0x7C, 0x40, 0x40, 0x7C, 0x04, 0x04, 0x7C,
    # 3
    0x7C, 0x40, 0x40, 0x7C, 0x40, 0x40, 0x7C,
    # 4
    0x44, 0x44, 0x44, 0x7C, 0x40, 0x40, 0x00,
    # 5
    0x7C, 0x04, 0x04, 0x7C, 0x40, 0x40, 0x7C,
    # 6
    0x7C, 0x04, 0x04, 0x7C, 0x44, 0x44, 0x7C,
    # 7
    0x7C, 0x40, 0x40, 0x40, 0x40, 0x40, 0x00,
    # 8
    0x7C, 0x44, 0x44, 0x7C, 0x44, 0x44, 0x7C,
    # 9
    0x7C, 0x44, 0x44, 0x7C, 0x40, 0x40, 0x7C,
]


class Asm:
    def __init__(self):
        self.code = []
        self.labels = {}
        self.patches = []
        self.abs_patches = []

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
        off = len(self.code) + 1
        self.patches.append((off, label, 'abs'))
        self.abs_patches.append(off)
        self.emit(0xC3, 0x00, 0x00)

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
                self.code[offset] = target & 0xFF
                self.code[offset + 1] = (target >> 8) & 0xFF

    def bytes(self):
        return list(self.code)


def lo(addr): return addr & 0xFF
def hi(addr): return (addr >> 8) & 0xFF


def build_routine():
    """Build MC: main game frame.

    Frame flow:
      1.   Clear pb+14 (miss byte)
      2.   Erase ball (restore NET_BYTE if on net col)
      2.5. Conditional score draw:
             if score_dirty OR ball_row < SCORE_ROWS: draw both digits, clear dirty
      3.   Delta left paddle: compute delta=py-old_py; if non-zero draw/erase
      3.5. P2 AI: update opy
      4.   Delta right paddle: compute delta=opy-old_opy; if non-zero draw/erase
      5.   Update col (wall bounce, miss, score increment, beep)
      6.   Update row (wall bounce)
      7.   Left paddle collision
      8.   Right paddle collision
      9.   Draw ball
      10.  Frame delay (BALL_DELAY=0 → effectively NOP)
      11.  LD A,0 / RET

    Delta paddle logic (for each paddle):
      delta = new_py - old_py  (signed byte, range -4..+4 for PADDLE_SPEED=4)
      if delta == 0: skip all LCD writes for this paddle
      if delta > 0 (moved down):
        erase delta rows starting at old_py (top of old paddle exposed)
        draw  delta rows starting at old_py+PADDLE_HEIGHT (new bottom rows)
      if delta < 0 (moved up):
        erase |delta| rows starting at old_py+PADDLE_HEIGHT-|delta| (bottom exposed)
        draw  |delta| rows starting at new_py (new top rows)
    """
    a = Asm()
    pb = PARAM_BASE

    # ------------------------------------------------------------------
    # 1. Clear miss byte
    # ------------------------------------------------------------------
    a.emit(0xAF)                           # XOR A
    a.emit(0x32, lo(pb+14), hi(pb+14))    # LD (miss),A

    # ------------------------------------------------------------------
    # 2. Erase ball at current (col, row); restore net byte if on net col
    # ------------------------------------------------------------------
    a.emit(0x3A, lo(pb+1), hi(pb+1))      # LD A,(row)
    a.emit(0x4F)                           # LD C,A
    a.emit(0x3A, lo(pb), hi(pb))           # LD A,(col)
    a.emit(0x47)                           # LD B,A
    a.emit(0x79)                           # LD A,C
    a.emit(0x48)                           # LD C,B
    a.emit_call('calc_vram')
    a.emit(0x06, 0x04)                     # LD B,4

    a.label('erase_ball_loop')
    a.emit(0xC5)
    a.emit_call('set_cursor')
    a.emit(0x79)                           # LD A,C
    a.emit(0xFE, NET_COL)
    a.emit_jr_cc(0x20, 'erase_zero')
    a.emit(0x3E, NET_BYTE)
    a.emit_jr_cc(0x18, 'erase_write')
    a.label('erase_zero')
    a.emit(0xAF)
    a.label('erase_write')
    a.emit_call('write_byte')
    a.emit_call('next_row')
    a.emit(0xC1)
    a.emit_djnz('erase_ball_loop')

    # ------------------------------------------------------------------
    # 2.5. Conditional score draw
    #   Draw if score_dirty != 0 OR ball_row < SCORE_ROWS
    # ------------------------------------------------------------------
    a.emit(0x3A, lo(pb+17), hi(pb+17))    # LD A,(score_dirty)
    a.emit(0xB7)                           # OR A
    a.emit_jr_cc(0x20, 'do_scores')        # JR NZ → score_dirty set, draw unconditionally
    # Z: dirty=0, check if ball overlaps score area
    a.label('check_ball_row')
    a.emit(0x3A, lo(pb+1), hi(pb+1))      # LD A,(ball_row)
    a.emit(0xFE, SCORE_ROWS)              # CP SCORE_ROWS
    a.emit_jr_cc(0x30, 'skip_scores')      # JR NC: ball >= SCORE_ROWS, skip

    a.label('do_scores')
    a.emit(0x3A, lo(pb+15), hi(pb+15))    # LD A,(S1)
    a.emit(0x0E, P1_SCORE_COL)
    a.emit_call('draw_digit')
    a.emit(0x3A, lo(pb+16), hi(pb+16))    # LD A,(S2)
    a.emit(0x0E, P2_SCORE_COL)
    a.emit_call('draw_digit')
    a.emit(0xAF)                           # XOR A
    a.emit(0x32, lo(pb+17), hi(pb+17))    # LD (score_dirty),0
    a.label('skip_scores')

    # ------------------------------------------------------------------
    # 3. Delta left paddle
    #   If ball col == PADDLE_COL the ball erase may have corrupted up to 4 paddle rows.
    #   Bypass delta entirely and do a full 12-row erase+draw to guarantee clean state.
    #   Otherwise use delta: only the changed edge rows are written.
    # ------------------------------------------------------------------
    a.emit(0x3A, lo(pb), hi(pb))          # LD A,(col) - current ball col
    a.emit(0xFE, PADDLE_COL)              # CP PADDLE_COL
    a.emit_jr_cc(0x20, 'lp_do_delta')     # JR NZ: ball not at left paddle col → delta path
    # Ball at PADDLE_COL: full erase old position + full draw new position
    a.emit(0x3A, lo(pb+11), hi(pb+11))    # LD A,(old_py)
    a.emit(0x0E, PADDLE_COL)              # LD C,PADDLE_COL
    a.emit_call('calc_vram')
    a.emit(0x06, PADDLE_HEIGHT)            # LD B,PADDLE_HEIGHT
    a.emit_call('erase_rows')
    a.emit(0x3A, lo(pb+10), hi(pb+10))    # LD A,(py)
    a.emit(0x0E, PADDLE_COL)
    a.emit_call('calc_vram')
    a.emit(0x06, PADDLE_HEIGHT)
    a.emit_call('draw_rows')
    a.emit(0x3A, lo(pb+10), hi(pb+10))    # save py → old_py
    a.emit(0x32, lo(pb+11), hi(pb+11))
    a.emit_jr_cc(0x18, 'lp_skip')         # JR lp_skip
    a.label('lp_do_delta')
    # Delta path
    a.emit(0x3A, lo(pb+10), hi(pb+10))    # LD A,(py)
    a.emit(0x47)                           # LD B,A  (B = py)
    a.emit(0x3A, lo(pb+11), hi(pb+11))    # LD A,(old_py)
    a.emit(0x90)                           # SUB B   A = old_py - py = -delta
    a.emit_jr_cc(0x28, 'lp_skip')         # JR Z: no change
    a.emit_jr_cc(0x38, 'lp_moved_up')     # JR C: carry set = moved down (old_py < py)

    # A = old_py - py.
    # If old_py > py (paddle moved up): result positive, no carry. A = |delta|
    # If old_py < py (paddle moved down): result negative (carry set). NEG → |delta|

    # No carry: old_py > py → paddle moved up → A is positive delta
    # Erase |delta| rows at bottom of old paddle: old_py + HEIGHT - delta
    # Draw  |delta| rows at top of new paddle: py
    a.emit(0x4F)                           # LD C,A  (C = |delta|, paddle moved up)
    # erase at old_py + PADDLE_HEIGHT - |delta| = py + PADDLE_HEIGHT (since old_py - delta = py)
    # old_py + HEIGHT - |delta|:  old_py is in (pb+11), read it
    a.emit(0x3A, lo(pb+11), hi(pb+11))    # LD A,(old_py)
    a.emit(0xC6, PADDLE_HEIGHT)            # ADD A,PADDLE_HEIGHT
    a.emit(0x91)                           # SUB C  = old_py+HEIGHT-|delta| = py+HEIGHT
    a.emit(0x0E, PADDLE_COL)              # LD C,PADDLE_COL  (col clobbered so set after)
    # A = start row for erase, C = col
    a.emit_call('calc_vram')
    # restore count into B
    a.emit(0x3A, lo(pb+10), hi(pb+10))    # LD A,(py) 
    a.emit(0x47)                           # B = py
    a.emit(0x3A, lo(pb+11), hi(pb+11))    # A = old_py
    a.emit(0x90)                           # SUB B  = |delta| again
    a.emit(0x47)                           # B = |delta|
    a.emit_call('erase_rows')
    # draw |delta| rows at new top: py
    a.emit(0x3A, lo(pb+10), hi(pb+10))    # LD A,(py)
    a.emit(0x0E, PADDLE_COL)
    a.emit_call('calc_vram')
    a.emit(0x3A, lo(pb+10), hi(pb+10))    # LD A,(py)
    a.emit(0x47)                           # B = py
    a.emit(0x3A, lo(pb+11), hi(pb+11))    # A = old_py
    a.emit(0x90)                           # SUB B = |delta|
    a.emit(0x47)                           # B = |delta|
    a.emit_call('draw_rows')
    a.emit_jr_cc(0x18, 'lp_done')         # JR lp_done

    a.label('lp_moved_up')
    # Carry set: old_py < py → paddle moved down → A = (old_py - py) is negative
    # NEG to get |delta| = py - old_py
    a.emit(0xED, 0x44)                     # NEG  A = py - old_py = |delta|
    a.emit(0x47)                           # LD B,A  (B = |delta|; calc_vram preserves B)
    # erase |delta| rows at top of old paddle: old_py
    a.emit(0x3A, lo(pb+11), hi(pb+11))    # LD A,(old_py)
    a.emit(0x0E, PADDLE_COL)              # LD C,PADDLE_COL
    a.emit_call('calc_vram')              # DE = VRAM(old_py, PADDLE_COL); B unchanged
    a.emit_call('erase_rows')             # B = |delta| ✓
    # draw |delta| rows at new bottom: py + PADDLE_HEIGHT - |delta|
    a.emit(0x3A, lo(pb+10), hi(pb+10))    # LD A,(py)
    a.emit(0x47)                           # B = py
    a.emit(0x3A, lo(pb+11), hi(pb+11))    # A = old_py
    a.emit(0x90)                           # SUB B = old_py - py (negative)
    a.emit(0xED, 0x44)                     # NEG → |delta|
    a.emit(0x4F)                           # C = |delta|
    a.emit(0x3A, lo(pb+10), hi(pb+10))    # A = py
    a.emit(0xC6, PADDLE_HEIGHT)            # ADD A, PADDLE_HEIGHT
    a.emit(0x91)                           # SUB C  = py + HEIGHT - |delta|
    a.emit(0x0E, PADDLE_COL)
    a.emit_call('calc_vram')
    a.emit(0x3A, lo(pb+10), hi(pb+10))    # A = py
    a.emit(0x47)                           # B = py
    a.emit(0x3A, lo(pb+11), hi(pb+11))    # A = old_py
    a.emit(0x90)                           # SUB B
    a.emit(0xED, 0x44)                     # NEG → |delta|
    a.emit(0x47)                           # B = |delta|
    a.emit_call('draw_rows')

    a.label('lp_done')
    # save py -> old_py
    a.emit(0x3A, lo(pb+10), hi(pb+10))
    a.emit(0x32, lo(pb+11), hi(pb+11))
    a.label('lp_skip')

    # ------------------------------------------------------------------
    # 3.5. P2 AI: update opy
    # ------------------------------------------------------------------
    a.emit(0x3A, lo(pb+12), hi(pb+12))    # LD A,(opy)
    a.emit(0x47)                           # B = opy
    a.emit(0x3A, lo(pb+1), hi(pb+1))      # LD A,(ball_row)
    a.emit(0x4F)                           # C = ball_row

    a.emit(0x78)                           # LD A,B
    a.emit(0xC6, 3)                        # ADD A,3
    a.emit(0xB9)                           # CP C
    a.emit_jr_cc(0x30, 'ai_chk_up')
    a.emit(0x78)
    a.emit(0xC6, PADDLE_SPEED)
    a.emit_jr_cc(0x18, 'ai_clamp')

    a.label('ai_chk_up')
    a.emit(0x79)
    a.emit(0xC6, 3)
    a.emit(0xB8)
    a.emit_jr_cc(0x30, 'ai_no_move')
    a.emit(0x78)
    a.emit(0xD6, PADDLE_SPEED)

    a.label('ai_clamp')
    a.emit(0xCB, 0x7F)                     # BIT 7,A
    a.emit_jr_cc(0x28, 'ai_chk_max')
    a.emit(0xAF)
    a.emit_jr_cc(0x18, 'ai_write')

    a.label('ai_chk_max')
    a.emit(0xFE, MAX_PADDLE_Y + 1)
    a.emit_jr_cc(0x38, 'ai_write')
    a.emit(0x3E, MAX_PADDLE_Y)

    a.label('ai_write')
    a.emit(0x32, lo(pb+12), hi(pb+12))
    a.label('ai_no_move')

    # ------------------------------------------------------------------
    # 4. Delta right paddle (same logic as left, using opy/old_opy/RIGHT_PADDLE_COL)
    # ------------------------------------------------------------------
    a.emit(0x3A, lo(pb), hi(pb))          # LD A,(col) - current ball col
    a.emit(0xFE, RIGHT_PADDLE_COL)        # CP RIGHT_PADDLE_COL
    a.emit_jr_cc(0x20, 'rp_do_delta')     # JR NZ: ball not at right paddle col → delta path
    # Ball at RIGHT_PADDLE_COL: full erase old position + full draw new position
    a.emit(0x3A, lo(pb+13), hi(pb+13))    # LD A,(old_opy)
    a.emit(0x0E, RIGHT_PADDLE_COL)
    a.emit_call('calc_vram')
    a.emit(0x06, PADDLE_HEIGHT)
    a.emit_call('erase_rows')
    a.emit(0x3A, lo(pb+12), hi(pb+12))    # LD A,(opy)
    a.emit(0x0E, RIGHT_PADDLE_COL)
    a.emit_call('calc_vram')
    a.emit(0x06, PADDLE_HEIGHT)
    a.emit_call('draw_rows')
    a.emit(0x3A, lo(pb+12), hi(pb+12))    # save opy → old_opy
    a.emit(0x32, lo(pb+13), hi(pb+13))
    a.emit_jr_cc(0x18, 'rp_skip')         # JR rp_skip
    a.label('rp_do_delta')
    # Delta path
    a.emit(0x3A, lo(pb+12), hi(pb+12))    # LD A,(opy)
    a.emit(0x47)                           # B = opy
    a.emit(0x3A, lo(pb+13), hi(pb+13))    # LD A,(old_opy)
    a.emit(0x90)                           # SUB B  A = old_opy - opy
    a.emit_jr_cc(0x28, 'rp_skip')
    a.emit_jr_cc(0x38, 'rp_moved_up')

    # no carry: old_opy > opy → moved up
    a.emit(0x4F)                           # C = |delta|
    a.emit(0x3A, lo(pb+13), hi(pb+13))
    a.emit(0xC6, PADDLE_HEIGHT)
    a.emit(0x91)                           # old_opy + HEIGHT - |delta| = opy+HEIGHT
    a.emit(0x0E, RIGHT_PADDLE_COL)
    a.emit_call('calc_vram')
    a.emit(0x3A, lo(pb+12), hi(pb+12))
    a.emit(0x47)
    a.emit(0x3A, lo(pb+13), hi(pb+13))
    a.emit(0x90)
    a.emit(0x47)                           # B = |delta|
    a.emit_call('erase_rows')
    a.emit(0x3A, lo(pb+12), hi(pb+12))    # draw at new top: opy
    a.emit(0x0E, RIGHT_PADDLE_COL)
    a.emit_call('calc_vram')
    a.emit(0x3A, lo(pb+12), hi(pb+12))
    a.emit(0x47)
    a.emit(0x3A, lo(pb+13), hi(pb+13))
    a.emit(0x90)
    a.emit(0x47)
    a.emit_call('draw_rows')
    a.emit_jr_cc(0x18, 'rp_done')

    a.label('rp_moved_up')
    # carry set: old_opy < opy → moved down
    a.emit(0xED, 0x44)                     # NEG
    a.emit(0x47)                           # LD B,A  (B = |delta|; calc_vram preserves B)
    a.emit(0x3A, lo(pb+13), hi(pb+13))    # LD A,(old_opy) - erase at old_opy top
    a.emit(0x0E, RIGHT_PADDLE_COL)        # LD C,RIGHT_PADDLE_COL
    a.emit_call('calc_vram')              # DE = VRAM(old_opy, RIGHT_PADDLE_COL); B unchanged
    a.emit_call('erase_rows')             # B = |delta| ✓
    # draw at opy + HEIGHT - |delta|
    a.emit(0x3A, lo(pb+12), hi(pb+12))
    a.emit(0x47)
    a.emit(0x3A, lo(pb+13), hi(pb+13))
    a.emit(0x90)
    a.emit(0xED, 0x44)
    a.emit(0x4F)                           # C = |delta|
    a.emit(0x3A, lo(pb+12), hi(pb+12))
    a.emit(0xC6, PADDLE_HEIGHT)
    a.emit(0x91)
    a.emit(0x0E, RIGHT_PADDLE_COL)
    a.emit_call('calc_vram')
    a.emit(0x3A, lo(pb+12), hi(pb+12))
    a.emit(0x47)
    a.emit(0x3A, lo(pb+13), hi(pb+13))
    a.emit(0x90)
    a.emit(0xED, 0x44)
    a.emit(0x47)
    a.emit_call('draw_rows')

    a.label('rp_done')
    a.emit(0x3A, lo(pb+12), hi(pb+12))
    a.emit(0x32, lo(pb+13), hi(pb+13))
    a.label('rp_skip')

    # ------------------------------------------------------------------
    # 5. Update col; miss byte + beep + score on walls
    # ------------------------------------------------------------------
    a.emit(0x3A, lo(pb), hi(pb))
    a.emit(0x47)
    a.emit(0x3A, lo(pb+2), hi(pb+2))
    a.emit(0x80)
    a.emit(0xFE, MAX_COL + 1)
    a.emit_jr_cc(0x38, 'col_ok')
    a.emit(0x3A, lo(pb+2), hi(pb+2))
    a.emit(0xED, 0x44)
    a.emit(0x32, lo(pb+2), hi(pb+2))
    a.emit(0x80)
    a.label('col_ok')
    a.emit(0x32, lo(pb), hi(pb))

    # P1 miss: col == 0 → S1++
    a.emit(0x3A, lo(pb), hi(pb))
    a.emit(0xB7)
    a.emit_jr_cc(0x20, 'no_p1miss')
    a.emit(0x3E, 0x01)
    a.emit(0x32, lo(pb+14), hi(pb+14))
    a.emit(0x21, lo(pb+15), hi(pb+15))
    a.emit(0x34)                           # INC (HL)
    a.emit(0x7E)                           # LD A,(HL)
    a.emit(0xFE, 10)
    a.emit_jr_cc(0x20, 'p1score_nowrap')
    a.emit(0x36, 0x00)
    a.label('p1score_nowrap')
    a.emit(0x3E, 0x01)                     # score_dirty = 1
    a.emit(0x32, lo(pb+17), hi(pb+17))
    a.emit(0x0E, 0x02)
    a.emit(0x1E, 0x07)
    a.emit(0xCD, 0x05, 0x00)
    a.label('no_p1miss')

    # P2 miss: col == MAX_COL → S2++
    a.emit(0x3A, lo(pb), hi(pb))
    a.emit(0xFE, MAX_COL)
    a.emit_jr_cc(0x20, 'no_p2miss')
    a.emit(0x3E, 0x02)
    a.emit(0x32, lo(pb+14), hi(pb+14))
    a.emit(0x21, lo(pb+16), hi(pb+16))
    a.emit(0x34)
    a.emit(0x7E)
    a.emit(0xFE, 10)
    a.emit_jr_cc(0x20, 'p2score_nowrap')
    a.emit(0x36, 0x00)
    a.label('p2score_nowrap')
    a.emit(0x3E, 0x01)                     # score_dirty = 1
    a.emit(0x32, lo(pb+17), hi(pb+17))
    a.emit(0x0E, 0x02)
    a.emit(0x1E, 0x07)
    a.emit(0xCD, 0x05, 0x00)
    a.label('no_p2miss')

    # ------------------------------------------------------------------
    # 6. Update row
    # ------------------------------------------------------------------
    a.emit(0x3A, lo(pb+1), hi(pb+1))
    a.emit(0x47)
    a.emit(0x3A, lo(pb+3), hi(pb+3))
    a.emit(0x80)
    a.emit(0xFE, MAX_ROW + 1)
    a.emit_jr_cc(0x38, 'chk_minrow')
    a.emit(0x3A, lo(pb+3), hi(pb+3))
    a.emit(0xED, 0x44)
    a.emit(0x32, lo(pb+3), hi(pb+3))
    a.emit(0x3E, MAX_ROW)
    a.emit_jr_cc(0x18, 'row_ok')
    a.label('chk_minrow')
    a.emit(0xFE, MIN_ROW)
    a.emit_jr_cc(0x30, 'row_ok')
    a.emit(0x3A, lo(pb+3), hi(pb+3))
    a.emit(0xED, 0x44)
    a.emit(0x32, lo(pb+3), hi(pb+3))
    a.emit(0x3E, MIN_ROW)
    a.label('row_ok')
    a.emit(0x32, lo(pb+1), hi(pb+1))

    # ------------------------------------------------------------------
    # 7. Left paddle collision
    # ------------------------------------------------------------------
    a.emit(0x3A, lo(pb), hi(pb))
    a.emit(0xFE, PADDLE_COL)
    a.emit_jr_cc(0x20, 'no_lpbounce')
    a.emit(0x3A, lo(pb+2), hi(pb+2))
    a.emit(0x3C)
    a.emit_jr_cc(0x20, 'no_lpbounce')

    a.emit(0x3A, lo(pb+10), hi(pb+10))
    a.emit(0x47)
    a.emit(0x3A, lo(pb+1), hi(pb+1))
    a.emit(0xC6, 0x03)
    a.emit(0xB8)
    a.emit_jr_cc(0x38, 'no_lpbounce')

    a.emit(0x3A, lo(pb+10), hi(pb+10))
    a.emit(0xC6, PADDLE_HEIGHT)
    a.emit(0x47)
    a.emit(0x3A, lo(pb+1), hi(pb+1))
    a.emit(0xB8)
    a.emit_jr_cc(0x30, 'no_lpbounce')

    a.emit(0x3A, lo(pb+2), hi(pb+2))
    a.emit(0xED, 0x44)
    a.emit(0x32, lo(pb+2), hi(pb+2))
    a.label('no_lpbounce')

    # ------------------------------------------------------------------
    # 8. Right paddle collision
    # ------------------------------------------------------------------
    a.emit(0x3A, lo(pb), hi(pb))
    a.emit(0xFE, RIGHT_PADDLE_COL)
    a.emit_jr_cc(0x20, 'no_rpbounce')
    a.emit(0x3A, lo(pb+2), hi(pb+2))
    a.emit(0x3D)
    a.emit_jr_cc(0x20, 'no_rpbounce')

    a.emit(0x3A, lo(pb+12), hi(pb+12))
    a.emit(0x47)
    a.emit(0x3A, lo(pb+1), hi(pb+1))
    a.emit(0xC6, 0x03)
    a.emit(0xB8)
    a.emit_jr_cc(0x38, 'no_rpbounce')

    a.emit(0x3A, lo(pb+12), hi(pb+12))
    a.emit(0xC6, PADDLE_HEIGHT)
    a.emit(0x47)
    a.emit(0x3A, lo(pb+1), hi(pb+1))
    a.emit(0xB8)
    a.emit_jr_cc(0x30, 'no_rpbounce')

    a.emit(0x3A, lo(pb+2), hi(pb+2))
    a.emit(0xED, 0x44)
    a.emit(0x32, lo(pb+2), hi(pb+2))
    a.label('no_rpbounce')

    # ------------------------------------------------------------------
    # 9. Draw ball
    # ------------------------------------------------------------------
    a.emit(0x3A, lo(pb), hi(pb))
    a.emit(0x4F)
    a.emit(0x3A, lo(pb+1), hi(pb+1))
    a.emit_call('calc_vram')
    a.emit(0x21, lo(pb+4), hi(pb+4))
    a.emit(0x06, 0x04)

    a.label('draw_ball_loop')
    a.emit(0xC5)
    a.emit_call('set_cursor')
    a.emit(0x7E)
    a.emit(0x23)
    a.emit_call('write_byte')
    a.emit(0xE5)
    a.emit_call('next_row')
    a.emit(0xE1)
    a.emit(0xC1)
    a.emit_djnz('draw_ball_loop')

    # ------------------------------------------------------------------
    # 10. Frame delay (BALL_DELAY=0 skips entirely)
    # ------------------------------------------------------------------
    if BALL_DELAY > 0:
        a.emit(0x2A, lo(pb+8), hi(pb+8))
        a.label('delay_loop')
        a.emit(0x2B)
        a.emit(0x7C)
        a.emit(0xB5)
        a.emit_jr_cc(0x20, 'delay_loop')

    # ------------------------------------------------------------------
    # 11. Return
    # ------------------------------------------------------------------
    a.emit(0x3E, 0x00)
    a.emit(0xC9)

    # ==================================================================
    # SUBROUTINES
    # ==================================================================

    a.label('erase_rows')
    a.emit(0xC5)
    a.emit_call('set_cursor')
    a.emit(0xAF)
    a.emit_call('write_byte')
    a.emit_call('next_row')
    a.emit(0xC1)
    a.emit_djnz('erase_rows')
    a.emit(0xC9)

    a.label('draw_rows')
    a.emit(0xC5)
    a.emit_call('set_cursor')
    a.emit(0x3E, PADDLE_BYTE)
    a.emit_call('write_byte')
    a.emit_call('next_row')
    a.emit(0xC1)
    a.emit_djnz('draw_rows')
    a.emit(0xC9)

    # ------------------------------------------------------------------
    # draw_digit: A=digit(0-9), C=byte-col
    # ------------------------------------------------------------------
    a.label('draw_digit')
    a.emit(0x5F)                           # LD E,A
    a.emit(0x16, 0x00)                     # LD D,0
    a.emit(0x62)                           # LD H,D
    a.emit(0x6B)                           # LD L,E
    a.emit(0x29)                           # ADD HL,HL  (×2)
    a.emit(0x19)                           # ADD HL,DE  (×3)
    a.emit(0x29)                           # ADD HL,HL  (×6)
    a.emit(0x19)                           # ADD HL,DE  (×7)
    off = len(a.code) + 1
    a.patches.append((off, 'digit_font', 'abs'))
    a.abs_patches.append(off)
    a.emit(0x11, 0x00, 0x00)               # LD DE,digit_font (patched)
    a.emit(0x19)                           # ADD HL,DE

    a.emit(0xE5)                           # PUSH HL
    a.emit(0x3E, 0x00)                     # LD A,0 (row 0)
    a.emit_call('calc_vram')
    a.emit(0xE1)                           # POP HL
    a.emit(0x06, SCORE_ROWS)

    a.label('draw_digit_loop')
    a.emit(0xC5)
    a.emit(0xE5)
    a.emit_call('set_cursor')
    a.emit(0xE1)
    a.emit(0x7E)
    a.emit(0x23)
    a.emit_call('write_byte')
    a.emit(0xE5)
    a.emit_call('next_row')
    a.emit(0xE1)
    a.emit(0xC1)
    a.emit_djnz('draw_digit_loop')
    a.emit(0xC9)

    a.label('next_row')
    a.emit(0x62)
    a.emit(0x6B)
    a.emit(0x11, 0x1E, 0x00)
    a.emit(0x19)
    a.emit(0xEB)
    a.emit(0xC9)

    a.label('calc_vram')
    a.emit(0x6F)
    a.emit(0x26, 0x00)
    a.emit(0x29)
    a.emit(0xE5)
    a.emit(0x29)
    a.emit(0x29)
    a.emit(0x29)
    a.emit(0x29)
    a.emit(0xD1)
    a.emit(0xB7)
    a.emit(0xED, 0x52)
    a.emit(0x59)
    a.emit(0x16, 0x00)
    a.emit(0x19)
    a.emit(0xEB)
    a.emit(0xC9)

    a.label('set_cursor')
    a.emit_call('wait_busy')
    a.emit(0x3E, 0x0A)
    a.emit(0xD3, 0x21)
    a.emit_call('wait_busy')
    a.emit(0x7B)
    a.emit(0xD3, 0x20)
    a.emit_call('wait_busy')
    a.emit(0x3E, 0x0B)
    a.emit(0xD3, 0x21)
    a.emit_call('wait_busy')
    a.emit(0x7A)
    a.emit(0xD3, 0x20)
    a.emit(0xC9)

    a.label('write_byte')
    a.emit(0xF5)
    a.emit_call('wait_busy')
    a.emit(0x3E, 0x0C)
    a.emit(0xD3, 0x21)
    a.emit_call('wait_busy')
    a.emit(0xF1)
    a.emit(0xD3, 0x20)
    a.emit(0xC9)

    a.label('wait_busy')
    a.emit(0xDB, 0x21)
    a.emit(0x07)
    a.emit(0x38, 0xFB)
    a.emit(0xC9)

    a.label('digit_font')
    for b in DIGIT_FONT:
        a.emit(b)

    a.resolve()
    return a


def main():
    asm = build_routine()
    mc_bytes = asm.bytes()
    mc_len = len(mc_bytes)
    patch_offsets = asm.abs_patches

    print(f"MC routine: {mc_len} bytes")
    print(f"Patch offsets ({len(patch_offsets)}): {patch_offsets}")

    n = mc_len if mc_len % 2 == 0 else mc_len + 1
    dim_d = (n // 2) - 1

    sprite    = [0x18, 0x3C, 0x3C, 0x18]
    delay     = BALL_DELAY
    start_col = 14
    start_row = 32
    start_dx  = 1
    start_dy  = 1
    start_py  = 26
    start_opy = 26

    NET_PX1  = 123
    NET_PX2  = 124
    LPAD_PX_LO = PADDLE_COL * 8
    LPAD_PX_HI = LPAD_PX_LO + 7
    RPAD_PX_LO = RIGHT_PADDLE_COL * 8
    RPAD_PX_HI = RPAD_PX_LO + 7

    out = []
    out.append("1 REM PONG2P - delta paddle + conditional score")
    out.append(f"2 REM Difficulty: {['EASY','MEDIUM','HARD'][DIFFICULTY]}  paddles col {PADDLE_COL}/{RIGHT_PADDLE_COL}")
    out.append("3 REM A/a=up  Z/z=down  ESC=exit")
    out.append("4 REM By kayto May 2026")
    out.append("5 CUROFF:SCREEN 1:CHAR1")

    out.append(f"6 DIM MC$({dim_d},1)")
    out.append("7 AD=VARPTR(MC$)-1")
    out.append(f"8 FOR I=0 TO {mc_len - 1}:READ V:POKE AD+I,V:NEXT I")
    out.append(f"9 FOR I=0 TO {len(patch_offsets) - 1}:READ P")
    out.append("10 L=PEEK(AD+P):H=PEEK(AD+P+1):W=L+H*256+AD")
    out.append("11 POKE AD+P,W-INT(W/256)*256:POKE AD+P+1,INT(W/256):NEXT I")

    out.append(f"14 POKE {PARAM_BASE},{start_col}")
    out.append(f"15 POKE {PARAM_BASE+1},{start_row}")
    out.append(f"16 POKE {PARAM_BASE+2},{start_dx}")
    out.append(f"17 POKE {PARAM_BASE+3},{start_dy}")
    for i, v in enumerate(sprite):
        out.append(f"{18+i} POKE {PARAM_BASE+4+i},{v}")
    out.append(f"22 POKE {PARAM_BASE+8},{delay & 0xFF}")
    out.append(f"23 POKE {PARAM_BASE+9},{(delay >> 8) & 0xFF}")
    out.append(f"24 POKE {PARAM_BASE+10},{start_py}:POKE {PARAM_BASE+11},{start_py}")
    out.append(f"25 POKE {PARAM_BASE+12},{start_opy}:POKE {PARAM_BASE+13},{start_opy}")
    out.append(f"26 POKE {PARAM_BASE+14},0:POKE {PARAM_BASE+15},0:POKE {PARAM_BASE+16},0")
    out.append(f"27 POKE {PARAM_BASE+17},1")  # score_dirty=1: draw scores on first frame

    out.append("28 FOR R=0 TO 63")
    out.append(f"29 PSET({NET_PX1},R):PSET({NET_PX2},R):NEXT R")

    out.append(f"30 FOR R={start_py} TO {start_py + PADDLE_HEIGHT - 1}")
    out.append(f"31 FOR X={LPAD_PX_LO} TO {LPAD_PX_HI}:PSET(X,R):NEXT X:NEXT R")
    out.append(f"32 FOR R={start_opy} TO {start_opy + PADDLE_HEIGHT - 1}")
    out.append(f"33 FOR X={RPAD_PX_LO} TO {RPAD_PX_HI}:PSET(X,R):NEXT X:NEXT R")

    out.append("34 DEFSEG=0")
    out.append("40 INKEY K")
    out.append("41 IF K=27 THEN GOTO 70")
    out.append(f"42 PY=PEEK({PARAM_BASE+10})")
    out.append("43 IF K=65 OR K=97 THEN PY=PY-4")
    out.append("44 IF PY<0 THEN PY=0")
    out.append("45 IF K=90 OR K=122 THEN PY=PY+4")
    out.append(f"46 IF PY>{MAX_PADDLE_Y} THEN PY={MAX_PADDLE_Y}")
    out.append(f"47 POKE {PARAM_BASE+10},PY")
    out.append("55 Z=CALL(AD)")
    out.append("60 GOTO 40")

    out.append("70 SCREEN 0:PRINT CHR$(1);:CURON:END")

    out.append(f"899 REM === Z80 machine code ({mc_len} bytes, ORG 0000H, patched at runtime) ===")
    ln = 900
    per_line = 15
    for i in range(0, len(mc_bytes), per_line):
        chunk = mc_bytes[i:i+per_line]
        out.append(f"{ln} DATA {','.join(str(b) for b in chunk)}")
        ln += 1

    out.append(f"{ln} REM === Patch table ({len(patch_offsets)} CALL/JP offsets, patched by lines 9-11) ===")
    out.append(f"{ln + 4} DATA {','.join(str(p) for p in patch_offsets)}")

    bas_path = Path("Progs/pong/2P/PONG2P.BAS")
    bas_path.write_text("\n".join(out) + "\n")
    print(f"\nWrote {bas_path} ({len(out)} lines)")

    result = subprocess.run(
        [sys.executable, "HBA_Format/hba_tokenize.py", str(bas_path), "HBA/PONG2P.HBA"],
        capture_output=True, text=True
    )
    print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())


if __name__ == "__main__":
    main()
