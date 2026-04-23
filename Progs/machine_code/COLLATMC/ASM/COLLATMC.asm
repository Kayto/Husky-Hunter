; COLLATMC.asm - Z80 Collatz sequence routine
; Source for the 33-byte MC inline in COLLATMC.BAS (POKEd at lines 32-36)
; By Kayto April 2026
; Licensed under the MIT License. See LICENSE file for details.
;
; No generator - bytes are hand-assembled directly into the BASIC POKE lines.
;
; Entry (via Hunter BASIC ARG/CALL interface):
;   E = seed high byte, C = seed low byte  (ARG sets both before CALL)
;   e.g. P=ARG(INT(N)) : S=CALL(62981)
; Exit:
;   A = step count (returned as result of CALL)
;
; Limits: seed intermediates must fit 16-bit (intermediates can exceed seed).
;         step count must be <= 255.
;   Safe test seeds: 27 (111 steps), 97 (118 steps), 171 (124 steps).
;
; MC loaded at F605H (62981) - user code area, 50 bytes reserved by OS.
; Uses 33 of the 50 available bytes.
;
; Assembler: compatible with Pasmo / SJASM+  (Intel-style, H-suffix hex)

ROUTINE_BASE    EQU     0F605H

                ORG     ROUTINE_BASE

                LD      H,E             ; HL = seed  (E=high, C=low from ARG)
                LD      L,C
                LD      B,0             ; B = step counter

; -------- MAIN LOOP --------
; Termination check: n=1 means done.
; H is tested first: if H!=0 then n>255 so n cannot be 1, skip the L check.
; This avoids a false positive (e.g. n=256 has H=1, L=0: L!=1 anyway, but
; checking H first is cheaper and makes the intent explicit).
loop:
                LD      A,H
                OR      A               ; sets Z if H = 0
                JR      NZ,step         ; H != 0: n > 255, cannot be 1
                LD      A,L
                CP      1               ; n = 1?
                JR      Z,done          ; yes: sequence complete

step:
                INC     B               ; step++

; Test parity: BIT 0,L sets Z if even
                BIT     0,L
                JR      NZ,odd          ; odd: go to 3n+1 branch

; Even: n = n / 2  (logical right-shift HL by 1)
                SRL     H
                RR      L
                JR      loop

; Odd: n = 3n + 1  (= 2n + n + 1 = HL+HL + old_HL + 1)
odd:
                PUSH    HL              ; save n
                ADD     HL,HL           ; HL = 2n
                POP     DE              ; DE = n
                ADD     HL,DE           ; HL = 3n
                INC     HL              ; HL = 3n + 1
                JR      loop

done:
                LD      A,B             ; A = step count  (returned by CALL)
                RET
