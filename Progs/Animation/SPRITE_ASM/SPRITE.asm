; SPRITE.asm - Byte-aligned sprite animation, fixed centre row
; Z80 source equivalent of gen_sprite.py
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

ROUTINE_BASE    EQU     0F605H
PARAM_BASE      EQU     0F740H
Y_BASE          EQU     840             ; row 28 * 30 = centre of 64-row display

col             EQU     PARAM_BASE + 0
sprite          EQU     PARAM_BASE + 1
delay_ctr       EQU     PARAM_BASE + 9  ; word, little-endian

                ORG     ROUTINE_BASE

; -------- MAIN LOOP --------
main_loop:
                LD      A,(col)         ; compute VRAM addr for current col
                LD      E,A             ; at fixed row 28 (Y_BASE = 840)
                LD      D,0
                LD      HL,Y_BASE
                ADD     HL,DE           ; HL = 840 + col
                EX      DE,HL           ; DE = VRAM addr
                LD      B,8

erase_loop:
                PUSH    BC
                CALL    set_cursor
                XOR     A               ; write 0 to erase
                CALL    write_byte
; DE += 30: copy DE->HL, add 30, copy back. No 16-bit ADD to DE directly on Z80.
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
                LD      (col),A

                LD      E,A             ; compute VRAM addr for new col
                LD      D,0
                LD      HL,Y_BASE
                ADD     HL,DE
                EX      DE,HL           ; DE = VRAM addr
                LD      HL,sprite       ; HL -> sprite pattern bytes
                LD      B,8

draw_loop:
                PUSH    BC
                CALL    set_cursor
                LD      A,(HL)
                INC     HL
                CALL    write_byte
; Double-EX trick: swap sprite_ptr into DE, add 30 to HL (was VRAM), swap back.
; Result: DE = VRAM+30, HL = sprite_ptr (both preserved).
                EX      DE,HL           ; HL = VRAM addr, DE = sprite ptr
                LD      BC,30
                ADD     HL,BC           ; HL = VRAM + 30
                EX      DE,HL           ; DE = VRAM+30, HL = sprite ptr
                POP     BC
                DJNZ    draw_loop

                LD      HL,(delay_ctr)  ; burn cycles for frame timing
delay_loop:
                DEC     HL
                LD      A,H
                OR      L
                JR      NZ,delay_loop

                LD      C,0BH
                CALL    0005H           ; BDOS fn11 - console status
                AND     A
                JP      Z,main_loop     ; no key: keep animating
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
                IN      A,(21H)         ; read status
                RLCA                    ; bit 7 -> carry
                JR      C,wait_busy     ; loop while busy
                RET
