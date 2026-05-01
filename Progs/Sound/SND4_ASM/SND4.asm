; SND4.asm - Port 86H bit-bang sound for Husky Hunter
; By Kayto April 2026
; Licensed under the MIT License. See LICENSE file for details.
;
; Assembler: compatible with Pasmo / SJASM+ (Intel-style, H-suffix hex)
;
; MC loaded via POKE loop at F605H (62981), 35 bytes.
; Parameters at F628H (63016) - 4 bytes:
;   +0 : pitch_lo  (low byte of half-period count)
;   +1 : pitch_hi  (high byte)
;   +2 : dur_lo    (low byte of full-cycle count)
;   +3 : dur_hi    (high byte)
;
; BASIC usage:
;   POKE 63016, pitch AND 255 : POKE 63017, INT(pitch/256)
;   POKE 63018, dur   AND 255 : POKE 63019, INT(dur/256)
;   X = CALL(62981)
;   equivalent to: SOUND pitch, dur
;
; ROM EVIDENCE:
;   BASIC SOUND handler at EPROM1:0x83CA uses OUT(86H) only.
;   OUT(86H) appears exactly twice in the entire ROM, both in the SOUND handler.
;   OUT(02H) appears zero times in the entire ROM.
;   No timers involved. Pure software bit-bang on CD4099BE latch.
;
; PITCH reference (same values as BASIC SOUND n arg):
;   A3=290  A4=144  B4=128  C5=121  D5=107  E5=95  F5=90  G5=80  A5=71

PARAM_PITCH     EQU     0F628H          ; half-period count word (LE)
PARAM_DUR       EQU     0F62AH          ; full-cycle count word  (LE)

                ORG     0F605H

; === Entry point ===

                LD      HL,(PARAM_PITCH)     ; HL = pitch (half-period delay count)
                EX      DE,HL               ; DE = pitch (temp)
                LD      HL,(PARAM_DUR)       ; HL = duration (full cycles)
                EX      DE,HL               ; HL = pitch, DE = duration

; === Tone loop: one iteration = one full cycle ===

TONE_LOOP:
                XOR     A
                OUT     (86H),A             ; port 86H LOW (first half-period)
                LD      B,H                 ; BC = pitch (half-period delay count)
                LD      C,L

; Half-period delay: ~26 T-states per iteration at 4 MHz

DELAY1:
                DEC     BC
                LD      A,B
                OR      C
                JR      NZ,DELAY1

                LD      A,01H
                OUT     (86H),A             ; port 86H HIGH (second half-period)
                LD      B,H
                LD      C,L

DELAY2:
                DEC     BC
                LD      A,B
                OR      C
                JR      NZ,DELAY2

                DEC     DE                  ; decrement full-cycle count
                LD      A,D
                OR      E
                JR      NZ,TONE_LOOP        ; loop until DE = 0

                RET

; === Parameters (F628H, immediately after code) ===
;   F628H (63016/63017): pitch word LE   POKE 63016 / 63017
;   F62AH (63018/63019): duration word LE  POKE 63018 / 63019

