; PONG.asm - 4x4 ball bouncing off all four LCD edges, no paddle
; Z80 source equivalent of gen_pong.py
; By Kayto April 2026
; Licensed under the MIT License. See LICENSE file for details.
;
; Assembler: compatible with Pasmo / SJASM+  (Intel-style, H-suffix hex)
;
; MC loaded at F605H (62981) by BASIC POKE loop.
; Params at F740H (63296):
;   +0     : col  (byte column, 0-29)
;   +1     : row  (pixel row, 0-60)
;   +2     : dx   (column delta: 1 or 0FFH = -1)
;   +3     : dy   (row delta:    1 or 0FFH = -1)
;   +4..+7 : sprite pattern (4 bytes, 4-row sprite)
;   +8,+9  : delay counter (little-endian word)
;
; Bounce: unsigned compare (CP N+1).  When out of range, NEG reverses
; the direction byte and the position is recomputed with the new delta.

ROUTINE_BASE    EQU     0F605H
PARAM_BASE      EQU     0F740H

MAX_COL         EQU     29              ; rightmost column (screen is 30 wide)
MAX_ROW         EQU     60              ; bottom row for 4-row sprite

col             EQU     PARAM_BASE + 0
row             EQU     PARAM_BASE + 1
dx              EQU     PARAM_BASE + 2
dy              EQU     PARAM_BASE + 3
sprite          EQU     PARAM_BASE + 4
delay_ctr       EQU     PARAM_BASE + 8  ; word, little-endian

                ORG     ROUTINE_BASE

; -------- MAIN LOOP --------
main_loop:
; Z80 has no LD C,(nn) - must go via A. Load both params then shuffle into place.
                LD      A,(row)         ; calc_vram wants: A=row, C=col
                LD      C,A             ; park row in C
                LD      A,(col)
                LD      B,A             ; park col in B
                LD      A,C             ; A = row
                LD      C,B             ; C = col
                CALL    calc_vram       ; DE = VRAM addr
                LD      B,4

erase_loop:
                PUSH    BC
                CALL    set_cursor
                XOR     A               ; A = 0: erase pixel data
                CALL    write_byte
                LD      H,D
                LD      L,E
                LD      BC,30
                ADD     HL,BC
                EX      DE,HL
                POP     BC
                DJNZ    erase_loop

; --- UPDATE col with horizontal bounce ---
                LD      A,(col)
                LD      B,A             ; B = old col
                LD      A,(dx)
                ADD     A,B             ; A = col + dx
                CP      MAX_COL+1       ; unsigned: 0..MAX_COL ok
                JR      C,col_ok
                LD      A,(dx)
                NEG                     ; reverse direction
                LD      (dx),A
                ADD     A,B             ; recompute with new dx
col_ok:
                LD      (col),A

; --- UPDATE row with vertical bounce ---
                LD      A,(row)
                LD      B,A             ; B = old row
                LD      A,(dy)
                ADD     A,B             ; A = row + dy
                CP      MAX_ROW+1
                JR      C,row_ok
                LD      A,(dy)
                NEG
                LD      (dy),A
                ADD     A,B
row_ok:
                LD      (row),A

; --- DRAW at new position ---
                LD      A,(col)
                LD      C,A             ; C = col
                LD      A,(row)         ; A = row
                CALL    calc_vram
                LD      HL,sprite
                LD      B,4

draw_loop:
                PUSH    BC
                CALL    set_cursor
                LD      A,(HL)
                INC     HL
                CALL    write_byte
                EX      DE,HL
                LD      BC,30
                ADD     HL,BC
                EX      DE,HL
                POP     BC
                DJNZ    draw_loop

                LD      HL,(delay_ctr)
delay_loop:
                DEC     HL
                LD      A,H
                OR      L
                JR      NZ,delay_loop

                LD      C,0BH
                CALL    0005H           ; BDOS fn11 - console status
                AND     A
                JP      Z,main_loop
                RET

; -------- calc_vram --------
; In:  A = row (0-63), C = col (0-29)
; Out: DE = row*30 + col
; row*30 = row*32 - row*2  (shift-and-subtract, no MUL)
; Clobbers A,HL,DE.  Preserves B,C
calc_vram:
                LD      L,A
                LD      H,0             ; HL = row
                ADD     HL,HL           ; row*2
                PUSH    HL              ; save row*2
                ADD     HL,HL           ; row*4
                ADD     HL,HL           ; row*8
                ADD     HL,HL           ; row*16
                ADD     HL,HL           ; row*32
                POP     DE              ; DE = row*2
                OR      A               ; OR A: clears carry flag without changing A
                SBC     HL,DE           ; HL = row*30
                LD      E,C             ; E = col
                LD      D,0
                ADD     HL,DE           ; HL = row*30 + col
                EX      DE,HL           ; DE = VRAM addr
                RET

; -------- set_cursor --------
; In:  DE = VRAM offset.  Clobbers A.  Preserves HL,DE,BC
set_cursor:
                CALL    wait_busy
                LD      A,0AH           ; cmd: cursor address low
                OUT     (21H),A
                CALL    wait_busy
                LD      A,E
                OUT     (20H),A
                CALL    wait_busy
                LD      A,0BH           ; cmd: cursor address high
                OUT     (21H),A
                CALL    wait_busy
                LD      A,D
                OUT     (20H),A
                RET

; -------- write_byte --------
; In:  A = byte to write.  Clobbers A.  Preserves HL,DE,BC
write_byte:
                PUSH    AF
                CALL    wait_busy
                LD      A,0CH           ; cmd: write display data
                OUT     (21H),A
                CALL    wait_busy
                POP     AF
                OUT     (20H),A
                RET

; -------- wait_busy --------
; Poll HD61830 status port until not busy (bit 7 = 0)
wait_busy:
                IN      A,(21H)
                RLCA
                JR      C,wait_busy
                RET
