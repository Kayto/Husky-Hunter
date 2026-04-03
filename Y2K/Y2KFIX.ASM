; Y2KFIX.ASM — Permanent Y2K century fix (8080/NSC800)
; By Nicola Cowie
; For Husky Hunter running DEMOS (CP/M 2.2)
; Assemble as Y.COM — run once after power on
;
; The ROM stores the default century as a 16-bit word
; (ASCII "19" = 3139h) at RAM address 0FA8Bh during
; power-up.  This patch overwrites it with "20" (3230h).
;
; Survives warm restart (Ctrl-C / DEMOS reset).
; Only needs re-running after a full power cycle.
;
; NOTE: Location 0FA8Bh is undocumented and may differ
;       on OS versions other than 9G06h.

        ORG     100H            ; CP/M .COM load address

START:  LXI     B, 3230H        ; ASCII "20" (B='2', C='0')
        LXI     H, 0FA8BH       ; Century word in RAM
        MOV     M, C             ; Low byte  '0' -> 0FA8Bh
        INX     H
        MOV     M, B             ; High byte '2' -> 0FA8Ch
        JMP     0                ; Warm boot back to DEMOS
