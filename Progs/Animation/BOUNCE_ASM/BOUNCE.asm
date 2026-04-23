; BOUNCE.asm - Wave-motion sprite, row follows sine table, column wraps 0-29
; Z80 source equivalent of gen_bounce.py
; By Kayto April 2026
; Licensed under the MIT License. See LICENSE file for details.
;
; Assembler: compatible with Pasmo / SJASM+  (Intel-style, H-suffix hex)
;
; MC loaded at F605H (62981) by BASIC POKE loop.
; Params at F740H (63296):
;   +0     : col  (byte column, 0-29)
;   +1..+8 : sprite pattern (8 bytes)
;   +9,+10 : delay counter (little-endian word)
;
; wave_table: 30-byte sine-derived Y positions embedded after code.
;   Formula: int(28 + 20*sin(col * 2*pi/30)), clamped 0-56.
;   Edit WAVE_CENTRE / WAVE_AMPLITUDE in gen_bounce.py to regenerate.

ROUTINE_BASE    EQU     0F605H
PARAM_BASE      EQU     0F740H

col             EQU     PARAM_BASE + 0
sprite          EQU     PARAM_BASE + 1
delay_ctr       EQU     PARAM_BASE + 9  ; word, little-endian

                ORG     ROUTINE_BASE

; -------- MAIN LOOP --------
main_loop:
                LD      A,(col)
                CALL    calc_vram       ; DE = VRAM addr for current col/row
                LD      B,8

erase_loop:
                PUSH    BC
                CALL    set_cursor
                XOR     A               ; write 0 to erase
                CALL    write_byte
                LD      H,D             ; DE += 30  (advance one LCD row)
                LD      L,E
                LD      BC,30
                ADD     HL,BC
                EX      DE,HL
                POP     BC
                DJNZ    erase_loop

                LD      A,(col)         ; increment col, wrap at 30
                INC     A
                CP      30
                JR      C,no_wrap
                XOR     A               ; wrap to 0
no_wrap:
                LD      (col),A         ; A = new col value (LD (nn),A preserves A)
                                        ; fall through with A = new col for calc_vram
                CALL    calc_vram       ; DE = VRAM addr for new col/row
                LD      HL,sprite
                LD      B,8

draw_loop:
                PUSH    BC
                CALL    set_cursor
                LD      A,(HL)
                INC     HL
                CALL    write_byte
                EX      DE,HL           ; DE += 30 via HL, preserving sprite ptr
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
; In:  A = col (0-29)
; Out: DE = wave_table[col]*30 + col
; Clobbers A,HL,DE,C.  Preserves B
calc_vram:
                LD      C,A             ; save col
                LD      E,A
                LD      D,0
                LD      HL,wave_table
                ADD     HL,DE           ; HL -> wave_table[col]
                LD      A,(HL)          ; A = row
                LD      L,A
                LD      H,0             ; row*30 = row*32 - row*2
                ADD     HL,HL           ; *2
                PUSH    HL              ; save row*2
                ADD     HL,HL           ; *4
                ADD     HL,HL           ; *8
                ADD     HL,HL           ; *16
                ADD     HL,HL           ; *32
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

; -------- wave_table (30 bytes) --------
; Sine-derived Y row per column.  Regenerate via gen_bounce.py.
wave_table:
                DB      28,32,36,39,42,45,47,47,47,47  ; cols  0- 9
                DB      45,42,39,36,32,28,23,19,16,13  ; cols 10-19
                DB      10, 8, 8, 8, 8,10,13,16,19,23  ; cols 20-29
