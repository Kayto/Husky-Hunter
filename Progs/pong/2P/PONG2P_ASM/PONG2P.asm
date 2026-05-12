; PONG2P.asm - Human vs AI pong with delta paddle rendering and conditional scoring
; Z80 source equivalent of gen_pong2P.py  build_routine()
; By Kayto May 2026
; Licensed under the MIT License. See LICENSE file for details.
;
; Assembler: compatible with Pasmo / sjasmplus (Intel-style, H-suffix hex)
;
; MC is stored in a Husky Hunter BASIC DIM/VARPTR string array.
; BASIC loads 906 bytes from DATA lines (900-960) into MC$, then patches
; all internal CALL/JP targets to absolute addresses before CALL(AD).
; CALL 0005H (CP/M BDOS vector) is NOT patched - 0005H is always live.
;
; Build: sjasmplus PONG2P.asm  (generates PONG2P.lst)
;        python asm_tools/lst_to_dlst.py PONG2P.lst > PONG2P.dlst
;
; ============================================================
; Parameter block at PARAM_BASE = F605H = 62981 (18 bytes)
;   +0  col         byte-column of ball (0..29)
;   +1  row         pixel-row of ball (1..60)
;   +2  dx          column delta: 01H (right) or 0FFH (left)
;   +3  dy          row delta:    01H (down)  or 0FFH (up)
;   +4  sprite[0]   ball pattern byte, row 0
;   +5  sprite[1]   ball pattern byte, row 1
;   +6  sprite[2]   ball pattern byte, row 2
;   +7  sprite[3]   ball pattern byte, row 3
;   +8  delay_lo    frame delay counter, low byte  (0 = max speed)
;   +9  delay_hi    frame delay counter, high byte
;   +10 py          left paddle top Y (0..MAX_PADDLE_Y)
;   +11 old_py      previous py, saved each frame by MC
;   +12 opy         right (AI) paddle top Y (0..MAX_PADDLE_Y)
;   +13 old_opy     previous opy, saved each frame by MC
;   +14 miss        miss flag: 00H=none, 01H=P1 missed, 02H=P2 missed
;   +15 S1          player 1 score (0..9, wraps at 10)
;   +16 S2          player 2 score (0..9, wraps at 10)
;   +17 score_dirty 01H = redraw scores this frame, 00H = conditional
; ============================================================

PARAM_BASE      EQU     0F605H

; Game constants (DIFFICULTY = 1, medium)
PADDLE_HEIGHT   EQU     12
PADDLE_SPEED    EQU     4
PADDLE_COL      EQU     4               ; left paddle byte-column
RIGHT_PADDLE_COL EQU    25              ; right paddle byte-column
MAX_PADDLE_Y    EQU     52              ; 64 - PADDLE_HEIGHT
MAX_COL         EQU     29
MIN_ROW         EQU     1
MAX_ROW         EQU     60
NET_COL         EQU     15
NET_BYTE        EQU     18H             ; 00011000b - two centre net pixels
PADDLE_BYTE     EQU     0FFH            ; full byte (all 8 pixels)
P1_SCORE_COL    EQU     7               ; column for left-side digit
P2_SCORE_COL    EQU     22              ; column for right-side digit
SCORE_ROWS      EQU     7               ; digit font height (rows 0..6)

; Named param addresses
col             EQU     PARAM_BASE + 0
row             EQU     PARAM_BASE + 1
dx              EQU     PARAM_BASE + 2
dy              EQU     PARAM_BASE + 3
sprite          EQU     PARAM_BASE + 4
delay_ctr       EQU     PARAM_BASE + 8
py              EQU     PARAM_BASE + 10
old_py          EQU     PARAM_BASE + 11
opy             EQU     PARAM_BASE + 12
old_opy         EQU     PARAM_BASE + 13
miss            EQU     PARAM_BASE + 14
S1              EQU     PARAM_BASE + 15
S2              EQU     PARAM_BASE + 16
score_dirty     EQU     PARAM_BASE + 17

; NOTE: ORG 0000H here means all addresses are offsets from the base of MC$.
; At runtime BASIC adds AD (the DIM/VARPTR base address) to every patched
; CALL/JP operand before CALL(AD) is executed.

                ORG     0000H

; ============================================================
; 1.  Clear miss flag
; ============================================================
                XOR     A               ; A = 0
                LD      (miss),A        ; clear miss flag for this frame

; ============================================================
; 2.  Erase ball
;     Overwrite the 4 rows the ball occupies with 0, except at
;     NET_COL where NET_BYTE (18H) is written to restore the net.
; ============================================================
                LD      A,(row)
                LD      C,A             ; C = row (temporary)
                LD      A,(col)
                LD      B,A             ; B = col (temporary)
                LD      A,C             ; A = row
                LD      C,B             ; C = col
                CALL    calc_vram       ; DE = VRAM offset for (row, col)
                LD      B,4             ; ball is 4 rows tall

erase_ball_loop:
                PUSH    BC
                CALL    set_cursor      ; position HD61830 to DE
                LD      A,C             ; A = ball column
                CP      NET_COL
                JR      NZ,erase_zero
                LD      A,NET_BYTE      ; restore the two centre net pixels
                JR      erase_write
erase_zero:
                XOR     A               ; erase: write zero
erase_write:
                CALL    write_byte
                CALL    next_row        ; DE += 30 (advance one LCD row)
                POP     BC
                DJNZ    erase_ball_loop

; ============================================================
; 2.5. Conditional score draw
;      Always draw if score_dirty != 0.
;      Also draw if ball row < SCORE_ROWS (ball overlaps digit area).
; ============================================================
                LD      A,(score_dirty)
                OR      A
                JR      NZ,do_scores    ; dirty flag set: draw unconditionally
                LD      A,(row)         ; check whether ball overlaps score rows
                CP      SCORE_ROWS      ; carry set if row < SCORE_ROWS
                JR      NC,skip_scores  ; no overlap: skip

do_scores:
                LD      A,(S1)
                LD      C,P1_SCORE_COL
                CALL    draw_digit      ; draw left score
                LD      A,(S2)
                LD      C,P2_SCORE_COL
                CALL    draw_digit      ; draw right score
                XOR     A
                LD      (score_dirty),A ; clear dirty flag

skip_scores:

; ============================================================
; 3.  Delta left paddle
;     If ball column == PADDLE_COL the erase above corrupted the
;     paddle pixels, so do a full erase+redraw of the old and new
;     paddle positions.  Otherwise use differential updates: only
;     the PADDLE_SPEED rows that changed are touched.
; ============================================================
                LD      A,(col)
                CP      PADDLE_COL
                JR      NZ,lp_do_delta  ; ball not at left paddle: delta path

; Ball overlaps left paddle column: full erase then full draw.
                LD      A,(old_py)
                LD      C,PADDLE_COL
                CALL    calc_vram
                LD      B,PADDLE_HEIGHT
                CALL    erase_rows
                LD      A,(py)
                LD      C,PADDLE_COL
                CALL    calc_vram
                LD      B,PADDLE_HEIGHT
                CALL    draw_rows
                LD      A,(py)
                LD      (old_py),A      ; save py -> old_py
                JR      lp_skip

lp_do_delta:
; Compute A = old_py - py (signed).
; No carry (>= 0): old_py > py -> paddle moved up.
; Carry set (< 0): old_py < py -> paddle moved down.
; Zero: no change.
                LD      A,(py)
                LD      B,A             ; B = py
                LD      A,(old_py)
                SUB     B               ; A = old_py - py
                JR      Z,lp_skip       ; no movement
                JR      C,lp_moved_down ; carry: old_py < py -> moved down

; --- Paddle moved up (no carry: old_py > py, A = positive delta) ---
; Erase delta rows at the bottom of the old position: old_py + HEIGHT - delta
; Draw  delta rows at the top of the new position:    py
                LD      C,A             ; C = delta (save before clobbering A)
                LD      A,(old_py)
                ADD     A,PADDLE_HEIGHT
                SUB     C               ; A = old_py + HEIGHT - delta = py + HEIGHT
                LD      C,PADDLE_COL
                CALL    calc_vram       ; DE = VRAM(py+HEIGHT, PADDLE_COL)
; Recompute delta into B (C was clobbered by LD C,PADDLE_COL; calc_vram preserves B)
                LD      A,(py)
                LD      B,A
                LD      A,(old_py)
                SUB     B               ; A = delta
                LD      B,A
                CALL    erase_rows      ; erase delta rows at old bottom
                LD      A,(py)
                LD      C,PADDLE_COL
                CALL    calc_vram       ; DE = VRAM(py, PADDLE_COL)
                LD      A,(py)
                LD      B,A
                LD      A,(old_py)
                SUB     B               ; A = delta
                LD      B,A
                CALL    draw_rows       ; draw delta rows at new top
                JR      lp_done

lp_moved_down:
; Carry: old_py < py -> paddle moved down.  NEG gives |delta| = py - old_py.
                NEG                     ; A = |delta|
                LD      B,A             ; B = |delta| (calc_vram preserves B)
; Erase |delta| rows at the top of the old position: old_py
                LD      A,(old_py)
                LD      C,PADDLE_COL
                CALL    calc_vram       ; B = |delta| unchanged
                CALL    erase_rows      ; erase |delta| rows at old top
; Draw |delta| rows at the new bottom: py + HEIGHT - |delta|
                LD      A,(py)
                LD      B,A             ; B = py
                LD      A,(old_py)
                SUB     B               ; old_py - py (negative)
                NEG                     ; |delta|
                LD      C,A             ; C = |delta|
                LD      A,(py)
                ADD     A,PADDLE_HEIGHT
                SUB     C               ; A = py + HEIGHT - |delta|
                LD      C,PADDLE_COL
                CALL    calc_vram
; Recompute |delta| into B
                LD      A,(py)
                LD      B,A
                LD      A,(old_py)
                SUB     B
                NEG                     ; |delta|
                LD      B,A
                CALL    draw_rows

lp_done:
                LD      A,(py)
                LD      (old_py),A      ; save py -> old_py
lp_skip:

; ============================================================
; 3.5. AI: move right paddle toward ball
;      Move PADDLE_SPEED rows per frame, clamp to 0..MAX_PADDLE_Y.
;      Target: ball row +/- 3 px tolerance (avoids jitter at centre).
; ============================================================
                LD      A,(opy)
                LD      B,A             ; B = opy
                LD      A,(row)
                LD      C,A             ; C = ball row
; If opy + 3 >= ball row we might need to move up; otherwise move down.
                LD      A,B
                ADD     A,3             ; A = opy + 3
                CP      C               ; opy+3 vs ball row
                JR      NC,ai_chk_up   ; opy+3 >= ball row: check if already above
                LD      A,B
                ADD     A,PADDLE_SPEED  ; move down by PADDLE_SPEED
                JR      ai_clamp

ai_chk_up:
; If ball row + 3 >= opy the paddle is already at the target zone: no move.
                LD      A,C
                ADD     A,3             ; A = ball row + 3
                CP      B               ; ball+3 vs opy
                JR      NC,ai_no_move   ; ball+3 >= opy: in zone, no move needed
                LD      A,B
                SUB     PADDLE_SPEED    ; move up by PADDLE_SPEED

ai_clamp:
; Clamp result to 0..MAX_PADDLE_Y.
                BIT     7,A             ; test sign bit (negative = underflow)
                JR      Z,ai_chk_max
                XOR     A               ; underflow: clamp to 0
                JR      ai_write
ai_chk_max:
                CP      MAX_PADDLE_Y+1  ; 53
                JR      C,ai_write      ; in range
                LD      A,MAX_PADDLE_Y  ; overflow: clamp to 52

ai_write:
                LD      (opy),A
ai_no_move:

; ============================================================
; 4.  Delta right paddle (same logic as section 3, using opy/old_opy)
; ============================================================
                LD      A,(col)
                CP      RIGHT_PADDLE_COL
                JR      NZ,rp_do_delta

; Ball overlaps right paddle column: full erase then full draw.
                LD      A,(old_opy)
                LD      C,RIGHT_PADDLE_COL
                CALL    calc_vram
                LD      B,PADDLE_HEIGHT
                CALL    erase_rows
                LD      A,(opy)
                LD      C,RIGHT_PADDLE_COL
                CALL    calc_vram
                LD      B,PADDLE_HEIGHT
                CALL    draw_rows
                LD      A,(opy)
                LD      (old_opy),A
                JR      rp_skip

rp_do_delta:
                LD      A,(opy)
                LD      B,A             ; B = opy
                LD      A,(old_opy)
                SUB     B               ; A = old_opy - opy
                JR      Z,rp_skip       ; no movement
                JR      C,rp_moved_down ; carry: old_opy < opy -> moved down

; --- Right paddle moved up ---
                LD      C,A             ; C = delta
                LD      A,(old_opy)
                ADD     A,PADDLE_HEIGHT
                SUB     C               ; A = old_opy + HEIGHT - delta
                LD      C,RIGHT_PADDLE_COL
                CALL    calc_vram
                LD      A,(opy)
                LD      B,A
                LD      A,(old_opy)
                SUB     B               ; A = delta
                LD      B,A
                CALL    erase_rows
                LD      A,(opy)
                LD      C,RIGHT_PADDLE_COL
                CALL    calc_vram
                LD      A,(opy)
                LD      B,A
                LD      A,(old_opy)
                SUB     B               ; A = delta
                LD      B,A
                CALL    draw_rows
                JR      rp_done

rp_moved_down:
                NEG                     ; A = |delta|
                LD      B,A
                LD      A,(old_opy)
                LD      C,RIGHT_PADDLE_COL
                CALL    calc_vram
                CALL    erase_rows
                LD      A,(opy)
                LD      B,A
                LD      A,(old_opy)
                SUB     B
                NEG                     ; |delta|
                LD      C,A
                LD      A,(opy)
                ADD     A,PADDLE_HEIGHT
                SUB     C               ; A = opy + HEIGHT - |delta|
                LD      C,RIGHT_PADDLE_COL
                CALL    calc_vram
                LD      A,(opy)
                LD      B,A
                LD      A,(old_opy)
                SUB     B
                NEG                     ; |delta|
                LD      B,A
                CALL    draw_rows

rp_done:
                LD      A,(opy)
                LD      (old_opy),A
rp_skip:

; ============================================================
; 5.  Update col (horizontal movement + wall bounce + miss/score)
;     dx = 01H (right) or 0FFH (-1, left).
;     Walls at col 0 (P1 misses) and col MAX_COL (P2 misses).
; ============================================================
                LD      A,(col)
                LD      B,A             ; B = current col
                LD      A,(dx)
                ADD     A,B             ; A = col + dx
                CP      MAX_COL+1       ; 30: carry set if A < 30 (in range)
                JR      C,col_ok
                LD      A,(dx)
                NEG                     ; flip direction
                LD      (dx),A
                ADD     A,B             ; recompute col with reversed dx
col_ok:
                LD      (col),A

; P1 miss: col == 0 -> increment S1, beep, set score_dirty
                LD      A,(col)
                OR      A               ; Z if col = 0
                JR      NZ,no_p1miss
                LD      A,01H
                LD      (miss),A        ; record P1 miss
                LD      HL,S1
                INC     (HL)            ; S1++
                LD      A,(HL)
                CP      10
                JR      NZ,p1score_nowrap
                LD      (HL),0          ; wrap at 10
p1score_nowrap:
                LD      A,01H
                LD      (score_dirty),A ; flag score for redraw
                LD      C,02H           ; BDOS fn 2: console output
                LD      E,07H           ; BEL character
                CALL    0005H
no_p1miss:

; P2 miss: col == MAX_COL -> increment S2, beep, set score_dirty
                LD      A,(col)
                CP      MAX_COL         ; 29
                JR      NZ,no_p2miss
                LD      A,02H
                LD      (miss),A        ; record P2 miss
                LD      HL,S2
                INC     (HL)            ; S2++
                LD      A,(HL)
                CP      10
                JR      NZ,p2score_nowrap
                LD      (HL),0          ; wrap at 10
p2score_nowrap:
                LD      A,01H
                LD      (score_dirty),A
                LD      C,02H
                LD      E,07H
                CALL    0005H
no_p2miss:

; ============================================================
; 6.  Update row (vertical movement + wall bounce at 1 and 60)
; ============================================================
                LD      A,(row)
                LD      B,A
                LD      A,(dy)
                ADD     A,B             ; A = row + dy
                CP      MAX_ROW+1       ; 61: carry set if A < 61
                JR      C,chk_minrow
                LD      A,(dy)
                NEG
                LD      (dy),A
                LD      A,MAX_ROW       ; clamp to 60
                JR      row_ok
chk_minrow:
                CP      MIN_ROW         ; 1: carry set if A < 1
                JR      NC,row_ok
                LD      A,(dy)
                NEG
                LD      (dy),A
                LD      A,MIN_ROW       ; clamp to 1
row_ok:
                LD      (row),A

; ============================================================
; 7.  Left paddle collision
;     Bounce dx if ball is at PADDLE_COL, moving left (dx = 0FFH),
;     and ball row is within py..py+PADDLE_HEIGHT-1 (with 3-row tolerance).
; ============================================================
                LD      A,(col)
                CP      PADDLE_COL
                JR      NZ,no_lpbounce
                LD      A,(dx)
                INC     A               ; dx = 0FFH (-1)? -> INC gives 0
                JR      NZ,no_lpbounce  ; not moving left: no bounce
; ball+3 must be >= py (ball is not entirely above paddle)
                LD      A,(py)
                LD      B,A
                LD      A,(row)
                ADD     A,3
                CP      B               ; (row+3) vs py
                JR      C,no_lpbounce   ; row+3 < py: above paddle
; ball row must be < py+PADDLE_HEIGHT (ball is not entirely below paddle)
                LD      A,(py)
                ADD     A,PADDLE_HEIGHT
                LD      B,A
                LD      A,(row)
                CP      B               ; row vs py+HEIGHT
                JR      NC,no_lpbounce  ; row >= py+HEIGHT: below paddle
                LD      A,(dx)
                NEG
                LD      (dx),A          ; reverse dx
no_lpbounce:

; ============================================================
; 8.  Right paddle collision
;     Bounce dx if ball is at RIGHT_PADDLE_COL, moving right (dx = 01H),
;     and ball row overlaps opy..opy+PADDLE_HEIGHT-1 (with 3-row tolerance).
; ============================================================
                LD      A,(col)
                CP      RIGHT_PADDLE_COL
                JR      NZ,no_rpbounce
                LD      A,(dx)
                DEC     A               ; dx = 01H (right)? -> DEC gives 0
                JR      NZ,no_rpbounce  ; not moving right: no bounce
                LD      A,(opy)
                LD      B,A
                LD      A,(row)
                ADD     A,3
                CP      B
                JR      C,no_rpbounce   ; row+3 < opy: above
                LD      A,(opy)
                ADD     A,PADDLE_HEIGHT
                LD      B,A
                LD      A,(row)
                CP      B
                JR      NC,no_rpbounce  ; row >= opy+HEIGHT: below
                LD      A,(dx)
                NEG
                LD      (dx),A
no_rpbounce:

; ============================================================
; 9.  Draw ball
;     Write the 4 sprite bytes to VRAM starting at (row, col).
; ============================================================
                LD      A,(col)
                LD      C,A
                LD      A,(row)
                CALL    calc_vram       ; DE = VRAM offset
                LD      HL,sprite       ; HL -> sprite data (patched by BASIC)
                LD      B,4             ; 4 rows

draw_ball_loop:
                PUSH    BC
                CALL    set_cursor
                LD      A,(HL)
                INC     HL
                CALL    write_byte
                PUSH    HL
                CALL    next_row        ; DE += 30
                POP     HL
                POP     BC
                DJNZ    draw_ball_loop

                LD      A,00H
                RET                     ; return to BASIC main loop

; ============================================================
; SUBROUTINE: erase_rows
;   In:  B = row count,  DE = VRAM start address
;   Writes 00H (erase) to B consecutive LCD rows.
; ============================================================
erase_rows:
                PUSH    BC
                CALL    set_cursor
                XOR     A               ; 00H = erase
                CALL    write_byte
                CALL    next_row        ; DE += 30
                POP     BC
                DJNZ    erase_rows
                RET

; ============================================================
; SUBROUTINE: draw_rows
;   In:  B = row count,  DE = VRAM start address
;   Writes PADDLE_BYTE (0FFH) to B consecutive LCD rows.
; ============================================================
draw_rows:
                PUSH    BC
                CALL    set_cursor
                LD      A,PADDLE_BYTE   ; 0FFH = solid paddle pixel
                CALL    write_byte
                CALL    next_row
                POP     BC
                DJNZ    draw_rows
                RET

; ============================================================
; SUBROUTINE: draw_digit
;   In:  A = digit (0..9),  C = byte-column
;   Draws a SCORE_ROWS-tall digit from digit_font at LCD rows 0..6.
;   Uses: all registers.  C must be set by caller before each call.
; ============================================================
draw_digit:
                LD      E,A             ; E = digit
                LD      D,0             ; DE = digit (16-bit)
                LD      H,D             ; H = 0
                LD      L,E             ; HL = digit
                ADD     HL,HL           ; HL = digit * 2
                ADD     HL,DE           ; HL = digit * 3
                ADD     HL,HL           ; HL = digit * 6
                ADD     HL,DE           ; HL = digit * 7  (byte offset in font)
                LD      DE,digit_font   ; DE = base address of font (patched by BASIC)
                ADD     HL,DE           ; HL -> first byte of this digit's 7 rows
                PUSH    HL              ; save font pointer
                LD      A,0             ; row 0 (top of screen)
                CALL    calc_vram       ; DE = VRAM(0, C)
                POP     HL              ; restore font pointer
                LD      B,SCORE_ROWS    ; B = 7

draw_digit_loop:
                PUSH    BC
                PUSH    HL
                CALL    set_cursor
                POP     HL
                LD      A,(HL)          ; load font pixel row
                INC     HL
                CALL    write_byte
                PUSH    HL
                CALL    next_row        ; DE += 30
                POP     HL
                POP     BC
                DJNZ    draw_digit_loop
                RET

; ============================================================
; SUBROUTINE: next_row
;   In/Out: DE = VRAM address.  Advances DE by 30 (one LCD pixel-row).
; ============================================================
next_row:
                LD      H,D
                LD      L,E
                LD      DE,001EH        ; 30 decimal
                ADD     HL,DE
                EX      DE,HL           ; DE = original + 30
                RET

; ============================================================
; SUBROUTINE: calc_vram
;   In:  A = pixel row (0..63),  C = byte-column (0..29)
;   Out: DE = row*30 + col  (HD61830 VRAM byte offset)
;   row*30 is computed as row*32 - row*2 using shift/subtract.
; ============================================================
calc_vram:
                LD      L,A             ; HL = row
                LD      H,0
                ADD     HL,HL           ; row * 2
                PUSH    HL              ; save row*2
                ADD     HL,HL           ; row * 4
                ADD     HL,HL           ; row * 8
                ADD     HL,HL           ; row * 16
                ADD     HL,HL           ; row * 32
                POP     DE              ; DE = row * 2
                OR      A               ; clear carry for SBC
                SBC     HL,DE           ; HL = row*32 - row*2 = row*30
                LD      E,C             ; E = col
                LD      D,0
                ADD     HL,DE           ; HL = row*30 + col
                EX      DE,HL           ; DE = VRAM offset
                RET

; ============================================================
; SUBROUTINE: set_cursor
;   In:  DE = VRAM offset.
;   Writes cursor address (low then high) to HD61830 via ports 21H/20H.
;   Commands: 0AH = SET CURSOR ADDRESS (low byte)
;             0BH = SET CURSOR ADDRESS (high byte)
; ============================================================
set_cursor:
                CALL    wait_busy
                LD      A,0AH           ; command: set cursor address low
                OUT     (21H),A
                CALL    wait_busy
                LD      A,E             ; low byte of VRAM offset
                OUT     (20H),A
                CALL    wait_busy
                LD      A,0BH           ; command: set cursor address high
                OUT     (21H),A
                CALL    wait_busy
                LD      A,D             ; high byte of VRAM offset
                OUT     (20H),A
                RET

; ============================================================
; SUBROUTINE: write_byte
;   In:  A = byte to write.
;   Sends WRITE DISPLAY DATA command (0CH) then the data byte.
; ============================================================
write_byte:
                PUSH    AF
                CALL    wait_busy
                LD      A,0CH           ; command: write display data
                OUT     (21H),A
                CALL    wait_busy
                POP     AF
                OUT     (20H),A         ; write data byte
                RET

; ============================================================
; SUBROUTINE: wait_busy
;   Polls HD61830 status port 21H.  Bit 7 = busy flag.
;   Loops until bit 7 is clear (controller ready).
; ============================================================
wait_busy:
                IN      A,(21H)
                RLCA                    ; rotate bit 7 into carry
                JR      C,wait_busy     ; carry set = still busy
                RET

; ============================================================
; DATA: digit_font
;   10 digits x 7 rows = 70 bytes.
;   Each byte is one LCD row, bit 0 = leftmost pixel of the byte-column.
;   Digits 0-9, each 7 rows tall, drawn at rows 0..6 of the screen.
; ============================================================
digit_font:
; 0: full box
                DB      7CH,44H,44H,44H,44H,44H,7CH
; 1: right-aligned vertical bar
                DB      10H,18H,10H,10H,10H,10H,38H
; 2: top-right, middle, bottom-left
                DB      7CH,40H,40H,7CH,04H,04H,7CH
; 3: top-right, middle, bottom-right
                DB      7CH,40H,40H,7CH,40H,40H,7CH
; 4: top sides, middle, right bar
                DB      44H,44H,44H,7CH,40H,40H,00H
; 5: top-left, middle, bottom-right
                DB      7CH,04H,04H,7CH,40H,40H,7CH
; 6: top-left, middle, full bottom
                DB      7CH,04H,04H,7CH,44H,44H,7CH
; 7: top bar, right bar
                DB      7CH,40H,40H,40H,40H,40H,00H
; 8: full box with middle bar
                DB      7CH,44H,44H,7CH,44H,44H,7CH
; 9: top box, bottom-right
                DB      7CH,44H,44H,7CH,40H,40H,7CH
