; PONGGAME.asm - Ball + net + left paddle with collision
; Z80 source equivalent of gen_ponggame.py
; By Kayto April 2026
; Licensed under the MIT License. See LICENSE file for details.
;
; Assembler: compatible with Pasmo / SJASM+  (Intel-style, H-suffix hex)
;
; MC stored in DIM/VARPTR string array (DIM MC$(D,1), AD=VARPTR(MC$)-1).
; Assembled with base=0. All internal CALL/JP targets are offset-from-start.
; BASIC patches them to real addresses at runtime before CALL(AD).
; EXCEPTION: CALL 0005H (BDOS) is NOT patched - 0005H is the real CP/M vector.
;
; Param block at F605H (62981) - fixed user code area (12 bytes):
;   +0     : col      (byte column, 0-29)
;   +1     : row      (pixel row, 0-60)
;   +2     : dx       (column delta: 1 or 0FFH = -1)
;   +3     : dy       (row delta:    1 or 0FFH = -1)
;   +4..+7 : sprite   (4 ball pattern bytes)
;   +8,+9  : delay    (frame delay counter, little-endian word)
;   +10    : py       (paddle Y, pixel row, 0-52)
;   +11    : old_py   (previous py, written by MC each frame)

PARAM_BASE      EQU     0F605H

PADDLE_HEIGHT   EQU     12      ; paddle height in pixel rows
PADDLE_SPEED    EQU     4       ; pixels per keypress
PADDLE_COL      EQU     1       ; left paddle column
MAX_PADDLE_Y    EQU     52      ; 64 - PADDLE_HEIGHT
MAX_COL         EQU     29
MAX_ROW         EQU     60
NET_COL         EQU     15      ; centre column
NET_BYTE        EQU     18H     ; centre 2 bits
PADDLE_BYTE     EQU     0FFH    ; full byte (8 pixels wide)
KEY_ESC         EQU     1BH
KEY_A           EQU     61H     ; 'a' after OR 20H (case-insensitive)
KEY_Z           EQU     7AH     ; 'z' after OR 20H

col             EQU     PARAM_BASE + 0
row             EQU     PARAM_BASE + 1
dx              EQU     PARAM_BASE + 2
dy              EQU     PARAM_BASE + 3
sprite          EQU     PARAM_BASE + 4
delay_ctr       EQU     PARAM_BASE + 8
py              EQU     PARAM_BASE + 10
old_py          EQU     PARAM_BASE + 11

; NOTE: ORG is base=0 here for clarity.
; At runtime BASIC adds AD (the DIM/VARPTR address) to all CALL/JP targets.
; This means every assembled CALL/JP target is an offset-from-start of the MC
; block, not a real address. BASIC iterates the patch table (DATA line 940) and
; rewrites each two-byte target as: real_addr = offset + AD.
                ORG     0000H

; ==================== INITIAL PADDLE DRAW ====================
; Drawn once before the main loop begins; execution falls straight through
; into main_loop. calc_vram takes A=row, C=col and returns DE = VRAM offset.
; draw_rows writes PADDLE_BYTE (0FFH = 8 pixels) to B consecutive rows.
                LD      A,(py)          ; A = initial paddle top row
                LD      C,PADDLE_COL    ; C = column 1
                CALL    calc_vram       ; DE = VRAM addr for top of paddle
                LD      B,PADDLE_HEIGHT ; B = 12 rows to draw
                CALL    draw_rows       ; write 0FFH to B rows

; ==================== MAIN LOOP ====================
main_loop:
                LD      A,(py)          ; save py for differential update
                LD      (old_py),A

; -------- KEY CHECK (non-blocking BDOS fn 11) --------
; BDOS function 11 (C=0BH): returns A=0 if no key waiting, A=0FFH if one is.
; Using AND A sets flags without changing A; JR Z skips the read if no key.
; This is non-blocking: the ball keeps moving even when no key is pressed.
                LD      C,0BH
                CALL    0005H           ; BDOS fn11: console status -> A
                AND     A               ; set Z flag if A=0 (no key)
                JR      Z,no_key        ; no key pending

; -------- READ KEY (BDOS fn 6, direct I/O) --------
; BDOS function 6 (C=06H) with E=0FFH: direct console input, returns char in A.
; Unlike fn1, fn6 does not echo the character to the screen.
                LD      C,06H
                LD      E,0FFH          ; E=0FFH = input mode for fn6
                CALL    0005H           ; A = key char

                CP      KEY_ESC
                JR      NZ,not_esc
                RET                     ; ESC: return to BASIC immediately

not_esc:
; OR 20H sets bit 5, converting uppercase A-Z (41H-5AH) to lowercase a-z
; (61H-7AH). Any key already lowercase is unchanged. This makes A/a and Z/z
; both work without separate comparisons.
                OR      20H             ; force lowercase (case-insensitive)
                CP      KEY_A           ; 'a' (61H)
                JR      Z,paddle_up
                CP      KEY_Z           ; 'z' (7AH)
                JR      Z,paddle_down
                JR      no_key          ; any other key: ignore

paddle_up:
; SUB sets carry if result would go negative (py < PADDLE_SPEED).
; JR NC: no carry means result >= 0, safe to store. If carry, clamp to 0.
                LD      A,(py)
                SUB     PADDLE_SPEED
                JR      NC,paddle_store ; no underflow: store result
                XOR     A               ; underflowed: clamp to 0 (top of screen)
                JR      paddle_store

paddle_down:
; ADD A,PADDLE_SPEED then compare to MAX_PADDLE_Y+1 (53).
; JR C: carry set means A < 53, i.e. within range. Otherwise clamp to 52.
                LD      A,(py)
                ADD     A,PADDLE_SPEED
                CP      MAX_PADDLE_Y+1  ; 53: A<53 means in range
                JR      C,paddle_store  ; in range: store
                LD      A,MAX_PADDLE_Y  ; overflowed: clamp to 52 (bottom limit)

paddle_store:
                LD      (py),A

no_key:

; -------- ERASE BALL --------
; Write zero to each of the 4 rows the ball occupies, EXCEPT at NET_COL where
; we write NET_BYTE (18H = 00011000b) to restore the two centre net pixels.
; calc_vram needs A=row and C=col. We load row then col via B as a temporary
; because we cannot LD C,(mem) directly on Z80 (no such opcode).
                LD      A,(row)         ; A = row
                LD      C,A             ; C = row (temporary)
                LD      A,(col)         ; A = col
                LD      B,A             ; B = col (temporary)
                LD      A,C             ; A = row  (restore for calc_vram)
                LD      C,B             ; C = col  (calc_vram expects col in C)
                CALL    calc_vram       ; DE = VRAM offset (row*30 + col)
                LD      B,4             ; 4 rows to erase (ball is 4 pixels tall)

erase_ball_loop:
; PUSH BC preserves both the loop counter (B) and ball column (C) across the
; CALL to set_cursor (which clobbers A but not BC via our calling convention).
                PUSH    BC
                CALL    set_cursor      ; position HD61830 cursor to DE
                LD      A,C             ; A = ball column (to test against NET_COL)
                CP      NET_COL         ; is ball at net column?
                JR      NZ,erase_ball_zero
                LD      A,NET_BYTE      ; yes: restore the two net centre pixels
                JR      erase_ball_write
erase_ball_zero:
                XOR     A               ; no: zero = erase
erase_ball_write:
                CALL    write_byte      ; write A to current cursor position
                CALL    next_row        ; DE += 30 (advance to next LCD row)
                POP     BC
                DJNZ    erase_ball_loop

; -------- PADDLE FIX --------
; If ball was on paddle column, the erase above wiped paddle pixels.
; Redraw full paddle at current py before the differential update.
                LD      A,(col)         ; old ball column
                CP      PADDLE_COL
                JR      NZ,no_paddle_fix
                LD      A,(py)
                LD      C,PADDLE_COL
                CALL    calc_vram
                LD      B,PADDLE_HEIGHT
                CALL    draw_rows
no_paddle_fix:

; -------- DIFFERENTIAL PADDLE UPDATE --------
; Rather than redrawing all 12 paddle rows every frame, only the PADDLE_SPEED
; (4) rows that change are touched. This halves flicker and LCD write traffic.
;
; Moved down by 4 rows:
;   old paddle: rows old_py .. old_py+11
;   new paddle: rows py     .. py+11      (py = old_py+4)
;   Overlap:    rows py     .. old_py+11  (unchanged middle 8 rows)
;   Action: erase top 4 of old (old_py..old_py+3), draw bottom 4 of new (py+8..py+11)
;
; Moved up by 4 rows:
;   Action: erase bottom 4 of old (old_py+8..old_py+11), draw top 4 of new (py..py+3)
                LD      A,(old_py)
                LD      B,A             ; B = old_py
                LD      A,(py)
                CP      B               ; compare new py against old py
                JR      Z,skip_paddle   ; py unchanged: skip all paddle drawing
                JR      C,moved_up      ; new py < old py: moved up

; Moved down: erase PADDLE_SPEED rows at top of old, draw at bottom of new.
                LD      A,B             ; A = old_py (top of old paddle)
                LD      C,PADDLE_COL
                CALL    calc_vram
                LD      B,PADDLE_SPEED
                CALL    erase_rows      ; blank the rows that scrolled off the top
                LD      A,(py)
                ADD     A,PADDLE_HEIGHT-PADDLE_SPEED  ; row = new bottom section start
                LD      C,PADDLE_COL
                CALL    calc_vram
                LD      B,PADDLE_SPEED
                CALL    draw_rows       ; fill the newly exposed bottom rows
                JR      skip_paddle

moved_up:
; Moved up: erase PADDLE_SPEED rows at bottom of old, draw at top of new.
                LD      A,B             ; A = old_py
                ADD     A,PADDLE_HEIGHT-PADDLE_SPEED  ; row = old bottom section start
                LD      C,PADDLE_COL
                CALL    calc_vram
                LD      B,PADDLE_SPEED
                CALL    erase_rows      ; blank the rows that scrolled off the bottom
                LD      A,(py)          ; A = new top row
                LD      C,PADDLE_COL
                CALL    calc_vram
                LD      B,PADDLE_SPEED
                CALL    draw_rows       ; fill the newly exposed top rows

skip_paddle:

; -------- UPDATE col (horizontal bounce, wall 0 and 29) --------
; dx is 1 (right) or 0FFH (-1, left). Adding 0FFH + B wraps unsigned:
; e.g. col=0, dx=0FFH: 0FFH+0=0FFH=255 which is >= MAX_COL+1 (30), triggering
; a bounce. Similarly col=29, dx=1: 29+1=30 >= 30, also bounces.
; After NEG, the new dx is applied to B (unchanged ball column) so the ball
; reflects in the same frame rather than sticking at the wall for one frame.
                LD      A,(col)
                LD      B,A             ; B = current col
                LD      A,(dx)          ; A = dx (1 or 0FFH)
                ADD     A,B             ; A = col + dx (unsigned arithmetic)
                CP      MAX_COL+1       ; compare to 30: C set if A < 30 (in range)
                JR      C,col_ok        ; in bounds: keep result
                LD      A,(dx)
                NEG                     ; out of bounds: flip direction
                LD      (dx),A
                ADD     A,B             ; recompute col with reversed dx
col_ok:
                LD      (col),A

; -------- BEEP ON MISS --------
; col == 0 means ball reached left wall (missed paddle).
                OR      A               ; Z if col = 0
                JR      NZ,no_beep
                LD      C,02H           ; BDOS fn2: console output
                LD      E,07H           ; BEL
                CALL    0005H
no_beep:

; -------- UPDATE row (vertical bounce, wall 0 and 60) --------
                LD      A,(row)
                LD      B,A
                LD      A,(dy)
                ADD     A,B
                CP      MAX_ROW+1
                JR      C,row_ok
                LD      A,(dy)
                NEG
                LD      (dy),A
                ADD     A,B
row_ok:
                LD      (row),A

; -------- PADDLE COLLISION CHECK --------
; Three conditions must ALL be true for a bounce:
;   1. Ball is at paddle column (col == PADDLE_COL)
;   2. Ball is moving left (dx == 0FFH = -1)
;   3. Ball vertically overlaps the paddle
;
; Overlap test (ball rows row..row+3, paddle rows py..py+11):
;   NOT above: row+3 >= py   i.e. (row+3 - py) does not borrow -> NC or Z
;   NOT below: row < py+12   i.e. (row - (py+12)) borrows -> C
                LD      A,(col)
                CP      PADDLE_COL      ; ball at paddle column?
                JR      NZ,no_pbounce   ; no: skip
                LD      A,(dx)
; INC A trick: dx=0FFH (-1) increments to 00H (Z flag set). Any other value
; (e.g. dx=01H) increments to non-zero. This tests dx==-1 without using CP.
                INC     A               ; 0FFH -> 00H only when dx = -1
                JR      NZ,no_pbounce   ; dx != -1: ball moving right, skip

; Check ball is not entirely above paddle: ball bottom edge (row+3) must be >= py
                LD      A,(py)
                LD      B,A             ; B = py
                LD      A,(row)
                ADD     A,3             ; A = row+3 (ball bottom edge, 0-indexed)
                CP      B               ; (row+3) - py: C if row+3 < py
                JR      C,no_pbounce    ; ball entirely above paddle: skip

; Check ball is not entirely below paddle: ball top (row) must be < py+12
                LD      A,(py)
                ADD     A,PADDLE_HEIGHT ; A = py + 12 (first row below paddle)
                LD      B,A
                LD      A,(row)
                CP      B               ; row - (py+12): NC if row >= py+12
                JR      NC,no_pbounce   ; ball entirely below paddle: skip

                ; Both overlap conditions passed: reverse dx
                LD      A,(dx)
                NEG                     ; 0FFH -> 01H (left -> right)
                LD      (dx),A
no_pbounce:

; -------- DRAW BALL --------
                LD      A,(col)
                LD      C,A
                LD      A,(row)
                CALL    calc_vram
                LD      HL,sprite
                LD      B,4

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

; -------- FRAME DELAY --------
; Busy-wait loop counts down a 16-bit value from delay_ctr to zero.
; DEC HL does not set the Z flag on Z80, so we test H|L explicitly.
; Higher delay_ctr = slower ball. 10000 (2710H) gives a playable speed.
                LD      HL,(delay_ctr)  ; load 16-bit delay value
delay_loop:
                DEC     HL
                LD      A,H
                OR      L               ; Z set only when both H and L are 0
                JR      NZ,delay_loop   ; loop until HL == 0

                JP      main_loop       ; JP used (not JR): distance > +127 bytes

; ==================== SUBROUTINES ====================

; erase_rows: write 0 to B rows starting at DE
; Entry: B = row count, DE = first VRAM offset
; Each iteration: set cursor, write 0x00, advance DE by 30, decrement B.
; PUSH/POP BC preserves the loop counter across the set_cursor/write_byte calls.
; Clobbers A,DE,BC
erase_rows:
                PUSH    BC
                CALL    set_cursor      ; position cursor to DE
                XOR     A               ; A = 0 (erase)
                CALL    write_byte
                CALL    next_row        ; DE += 30
                POP     BC
                DJNZ    erase_rows      ; decrement B, loop if non-zero
                RET

; draw_rows: write 0FFH to B rows starting at DE
; Entry: B = row count, DE = first VRAM offset
; Identical structure to erase_rows but writes PADDLE_BYTE (0FFH = all 8 pixels).
; Clobbers A,DE,BC
draw_rows:
                PUSH    BC
                CALL    set_cursor
                LD      A,PADDLE_BYTE   ; A = 0FFH (all 8 pixels lit)
                CALL    write_byte
                CALL    next_row        ; DE += 30
                POP     BC
                DJNZ    draw_rows
                RET

; next_row: DE += 30  (advance one LCD row)
; The LCD VRAM is 30 bytes wide, so adding 30 moves to the same column on the
; next row. Z80 has no ADD DE,n, so we copy DE to HL, add, then EX DE,HL.
; Clobbers HL.  Preserves DE value after add.
next_row:
                LD      H,D
                LD      L,E             ; HL = DE
                LD      DE,30
                ADD     HL,DE           ; HL += 30
                EX      DE,HL           ; DE = HL (result back in DE)
                RET

; calc_vram: A=row, C=col -> DE = row*30 + col
; Multiply by 30 using shift-and-subtract: 30 = 32 - 2
;   1. HL = row           (LD L,A / LD H,0)
;   2. HL = row*2         (ADD HL,HL)  <- saved to stack
;   3. HL = row*4, *8, *16, *32 (three more ADD HL,HL)
;   4. DE = row*2        (POP DE)
;   5. HL = row*32 - row*2 = row*30  (SBC HL,DE, carry cleared by OR A)
;   6. DE = col           (LD E,C / LD D,0)
;   7. HL += DE           -> row*30 + col
;   8. EX DE,HL           -> DE = VRAM offset
; SBC HL,DE needs carry=0; OR A clears carry without changing A.
; Clobbers A,HL,DE.  Preserves B,C
calc_vram:
                LD      L,A
                LD      H,0             ; HL = row
                ADD     HL,HL           ; HL = row*2
                PUSH    HL              ; save row*2 for later
                ADD     HL,HL           ; HL = row*4
                ADD     HL,HL           ; HL = row*8
                ADD     HL,HL           ; HL = row*16
                ADD     HL,HL           ; HL = row*32
                POP     DE              ; DE = row*2
                OR      A               ; clear carry flag (OR A never sets carry)
                SBC     HL,DE           ; HL = row*32 - row*2 = row*30
                LD      E,C
                LD      D,0             ; DE = col
                ADD     HL,DE           ; HL = row*30 + col
                EX      DE,HL           ; DE = VRAM offset
                RET

; set_cursor: DE = VRAM offset -> set HD61830 cursor position
; HD61830 I/O protocol:
;   Port 21H = command/status register (write cmd, read status)
;   Port 20H = data register (write data after command)
; To set cursor address (two-byte VRAM offset):
;   OUT (21H), 0AH  ; command: set cursor address low byte
;   OUT (20H), E    ; data: low byte of offset
;   OUT (21H), 0BH  ; command: set cursor address high byte
;   OUT (20H), D    ; data: high byte of offset
; Each command/data write must be preceded by wait_busy.
; Clobbers A.  Preserves HL,DE,BC
set_cursor:
                CALL    wait_busy
                LD      A,0AH           ; cmd 0AH: cursor address low
                OUT     (21H),A
                CALL    wait_busy
                LD      A,E             ; low byte of VRAM offset
                OUT     (20H),A
                CALL    wait_busy
                LD      A,0BH           ; cmd 0BH: cursor address high
                OUT     (21H),A
                CALL    wait_busy
                LD      A,D             ; high byte of VRAM offset
                OUT     (20H),A
                RET

; write_byte: A = byte -> write to HD61830 VRAM at current cursor
; Sends command 0CH (write display data) then the byte.
; The HD61830 auto-increments its cursor after each write, but we manage
; position explicitly via set_cursor to handle multi-row sprites.
; Clobbers A.  Preserves HL,DE,BC
write_byte:
                PUSH    AF              ; save byte to write
                CALL    wait_busy
                LD      A,0CH           ; cmd 0CH: write display data
                OUT     (21H),A
                CALL    wait_busy
                POP     AF              ; restore byte
                OUT     (20H),A         ; write byte to VRAM
                RET

; wait_busy: poll HD61830 status register until controller is not busy
; Status byte read from port 21H: bit 7 = busy flag (1 = busy, 0 = ready).
; RLCA rotates A left, moving bit 7 into the carry flag.
; JR C loops while carry is set (controller busy).
wait_busy:
                IN      A,(21H)         ; read HD61830 status
                RLCA                    ; rotate bit 7 into carry
                JR      C,wait_busy     ; carry set = busy: poll again
                RET
