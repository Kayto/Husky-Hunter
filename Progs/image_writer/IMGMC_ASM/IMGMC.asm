; IMGMC.asm - MC-accelerated HD61830 LCD blast
; Z80 source equivalent of gen_imgmc.py
; By Kayto April 2026
; Licensed under the MIT License. See LICENSE file for details.
;
; Assembler: compatible with Pasmo / SJASM+  (Intel-style, H-suffix hex)
;
; MC loaded at F605H (62981) by BASIC POKE loop (30 bytes).
; No parameter block - HL and DE are hard-coded.
;
; Phase 1 (BASIC): bit-reversed image data POKEd into RAM at C000H (1920 bytes).
; Phase 2 (MC):    this routine blasts the buffer to the HD61830 via I/O.
;
; Writes entire 240x64 LCD (1920 bytes = 30 cols * 64 rows) in ~13ms.
; Note: HD61830 auto-increments its display address register after each
; CMD_WRITE data byte - no set_cursor call needed per byte.

ROUTINE_BASE    EQU     0F605H
BUF_ADDR        EQU     0C000H          ; image buffer in RAM
BUF_LEN         EQU     0780H           ; 1920 = 30*64

LCD_DATA        EQU     20H             ; HD61830 data port
LCD_CMD         EQU     21H             ; HD61830 command/status port
CMD_WRITE       EQU     0CH             ; HD61830 cmd: write display data

                ORG     ROUTINE_BASE

                LD      HL,BUF_ADDR     ; source: image buffer
                LD      DE,BUF_LEN      ; byte count: 1920

; wait_busy is inlined at both call sites (saves 2 bytes vs CALL+subroutine)
blast_loop:
busy1:          IN      A,(LCD_CMD)     ; poll HD61830 status: bit 7 = busy
                RLCA
                JR      C,busy1         ; loop while busy (offset -5)
                LD      A,CMD_WRITE     ; cmd: write display data
                OUT     (LCD_CMD),A
busy2:          IN      A,(LCD_CMD)     ; poll again before data write
                RLCA
                JR      C,busy2         ; loop while busy (offset -5)
                LD      A,(HL)          ; next byte from buffer
                OUT     (LCD_DATA),A
                INC     HL
                DEC     DE
                LD      A,D
                OR      E
                JR      NZ,blast_loop   ; loop until DE = 0  (offset -23)
                RET
