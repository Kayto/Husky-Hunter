; DEFEND.asm - Z80 source equivalent of gen_defend11.py
; DEFENDER game engine (Prerelease v0.1) for the Husky Hunter
; By Kayto April/May 2026
; Licensed under the MIT License. See LICENSE file for details.
;
; Compatible with sjasmplus (Intel-style H-suffix hex).
;
; Assemble with base address 0. All internal CALL/JP targets are
; relative to start. BASIC patches them to real addresses at runtime
; (patch loop, lines 9-11 of DefDat1.BAS).
; EXCEPTION: CALL 0005H (CP/M BDOS vector) is NOT patched.
;
; MC stored as: DIM MC$(717,1) ; AD=VARPTR(MC$)-1
;               1435 bytes at AD..AD+1434
; Called by:   Z=CALL(AD)
;
; Build: sjasmplus DEFEND.asm  (generates DEFEND.lst)
;        python asm_tools/lst_to_dlst.py DEFEND.lst > DEFEND.dlst
;
; Param block at F605H (62981) - fixed user code area:
;   +0         ship_row           current row of ship (0-56)
;   +1         old_row            previous ship row (for erase)
;   +2..+9     ship_sprite        8 bytes: 01 07 1F FF FF 1F 07 01
;   +10,+11    frame_delay        little-endian word (5000 = 1388H)
;   +12        star1_col          star 1 column (0-29)
;   +13        star1_row          star 1 row    (0-56)
;   +14        star2_col          star 2 column
;   +15        star2_row          star 2 row
;   +16        star3_col          star 3 column
;   +17        star3_row          star 3 row
;   +18        rng_seed           star RNG seed
;   +19        shot_col           laser bolt column
;   +20        shot_row           laser bolt row
;   +21        shot_active        0=none, 1=in flight
;   +22        enemy1_col         enemy 1 column
;   +23        enemy1_row         enemy 1 row
;   +24        enemy1_active      0=waiting, 1=on screen
;   +25        enemy1_phase       movement phase (0-3 mod)
;   +26..+33   enemy_sprite       8 bytes (shared): 1C A0 3E F1 F1 3E A0 1C
;   +34        enemy1_dy          direction: 01=down, FF=up
;   +35        enemy2_col         enemy 2 column
;   +36        enemy2_row         enemy 2 row
;   +37        enemy2_active      0=waiting, 1=on screen
;   +38        enemy2_phase       movement phase
;   +39        enemy2_dy          direction: 01=down, FF=up
;   +40        kill_count         enemies destroyed (score, 0-FF)
;   +41        wave               0=wave1, 1=wave2 (enemy2 enabled)
;   +42        lives              lives remaining (0-3)
;   +43        player_dead        0=alive, 1=dead (set by collision)
;   +44..+51   heart_sprite       8 bytes: 36 7E 7E 3C 18 10 00 00
;   +52        event_code         0=none 1=laser 2=explosion 3=death
;
;   Total: 53 bytes. Hardware limit: 80 bytes.
;
; BDOS entry: 0005H. BASIC uses fn=0BH (key available?), fn=06H (read key).
;   LD C,0BH ; CALL 0005H ; test A
;   LD C,06H ; LD E,0FFH  ; CALL 0005H -> A = key char

; ============================================================
;  EQUATES
; ============================================================

PARAM_BASE      EQU     0F605H

ship_row        EQU     PARAM_BASE+0
old_row         EQU     PARAM_BASE+1
ship_sprite     EQU     PARAM_BASE+2
frame_delay     EQU     PARAM_BASE+10
star1_col       EQU     PARAM_BASE+12
star1_row       EQU     PARAM_BASE+13
star2_col       EQU     PARAM_BASE+14
star2_row       EQU     PARAM_BASE+15
star3_col       EQU     PARAM_BASE+16
star3_row       EQU     PARAM_BASE+17
rng_seed        EQU     PARAM_BASE+18
shot_col        EQU     PARAM_BASE+19
shot_row        EQU     PARAM_BASE+20
shot_active     EQU     PARAM_BASE+21
enemy1_col      EQU     PARAM_BASE+22
enemy1_row      EQU     PARAM_BASE+23
enemy1_active   EQU     PARAM_BASE+24
enemy1_phase    EQU     PARAM_BASE+25
enemy_sprite    EQU     PARAM_BASE+26   ; 8 bytes, shared between enemies
enemy1_dy       EQU     PARAM_BASE+34
enemy2_col      EQU     PARAM_BASE+35
enemy2_row      EQU     PARAM_BASE+36
enemy2_active   EQU     PARAM_BASE+37
enemy2_phase    EQU     PARAM_BASE+38
enemy2_dy       EQU     PARAM_BASE+39
kill_count      EQU     PARAM_BASE+40
wave            EQU     PARAM_BASE+41
lives           EQU     PARAM_BASE+42
player_dead     EQU     PARAM_BASE+43
heart_sprite    EQU     PARAM_BASE+44   ; 8 bytes
event_code      EQU     PARAM_BASE+52

SHIP_COL        EQU     2
SHIP_HEIGHT     EQU     8
ENEMY_HEIGHT    EQU     8
SHIP_SPEED      EQU     2
MAX_COL         EQU     29
MAX_ROW         EQU     56
HEART_COL       EQU     0
STAR_BYTE_TOP   EQU     03H
STAR_BYTE_BOT   EQU     01H
SHOT_BYTE_TOP   EQU     3CH
SHOT_BYTE_BOT   EQU     3CH
WAVE2_THRESHOLD EQU     5
KEY_A           EQU     61H
KEY_Z           EQU     7AH
KEY_SPACE       EQU     20H
KEY_ESC         EQU     1BH
BDOS            EQU     0005H
LCD_CMD         EQU     21H
LCD_DATA        EQU     20H

; ============================================================
;  ENTRY POINT: draw ship at initial position
; ============================================================

                ORG     0000H

                LD      A,(ship_row)
                LD      C,SHIP_COL
                CALL    calc_vram
                LD      HL,ship_sprite
                LD      B,SHIP_HEIGHT
                CALL    draw_sprite

; ============================================================
;  MAIN LOOP
; ============================================================

main_loop:

; --- Star 1: erase old position ---
; A=row, C=col -> calc_vram uses A=row, C=col
; Load col into B first; row into A; LD C,B copies col into C
                LD      A,(star1_col)
                LD      B,A
                LD      A,(star1_row)
                LD      C,B
                CALL    calc_vram
                CALL    set_cursor
                XOR     A
                CALL    write_byte
                CALL    next_row
                CALL    set_cursor
                XOR     A
                CALL    write_byte
; --- Star 1: scroll (move left), wrap at col 0 ---
                LD      A,B             ; A = old col (B still holds it)
                OR      A               ; test zero
                JR      Z,s1_wrap
                DEC     A
                JR      s1_store
s1_wrap:
                LD      A,(rng_seed)
                ADD     A,11H
                LD      (rng_seed),A
                AND     3EH
                LD      (star1_row),A
                LD      A,MAX_COL       ; reset to right edge
s1_store:
                LD      (star1_col),A
                LD      B,A             ; save new col in B
; --- Star 1: draw at new position ---
                LD      A,(star1_row)
                LD      C,B
                CALL    calc_vram
                CALL    set_cursor
                LD      A,STAR_BYTE_TOP
                CALL    write_byte
                CALL    next_row
                CALL    set_cursor
                LD      A,STAR_BYTE_BOT
                CALL    write_byte

; --- Star 2: erase old position ---
                LD      A,(star2_col)
                LD      B,A
                LD      A,(star2_row)
                LD      C,B
                CALL    calc_vram
                CALL    set_cursor
                XOR     A
                CALL    write_byte
                CALL    next_row
                CALL    set_cursor
                XOR     A
                CALL    write_byte
; --- Star 2: scroll and wrap ---
                LD      A,B
                OR      A
                JR      Z,s2_wrap
                DEC     A
                JR      s2_store
s2_wrap:
                LD      A,(rng_seed)
                ADD     A,11H
                LD      (rng_seed),A
                AND     3EH
                LD      (star2_row),A
                LD      A,MAX_COL
s2_store:
                LD      (star2_col),A
                LD      B,A
; --- Star 2: draw at new position ---
                LD      A,(star2_row)
                LD      C,B
                CALL    calc_vram
                CALL    set_cursor
                LD      A,STAR_BYTE_TOP
                CALL    write_byte
                CALL    next_row
                CALL    set_cursor
                LD      A,STAR_BYTE_BOT
                CALL    write_byte

; --- Star 3: erase old position ---
                LD      A,(star3_col)
                LD      B,A
                LD      A,(star3_row)
                LD      C,B
                CALL    calc_vram
                CALL    set_cursor
                XOR     A
                CALL    write_byte
                CALL    next_row
                CALL    set_cursor
                XOR     A
                CALL    write_byte
; --- Star 3: scroll and wrap ---
                LD      A,B
                OR      A
                JR      Z,s3_wrap
                DEC     A
                JR      s3_store
s3_wrap:
                LD      A,(rng_seed)
                ADD     A,11H
                LD      (rng_seed),A
                AND     3EH
                LD      (star3_row),A
                LD      A,MAX_COL
s3_store:
                LD      (star3_col),A
                LD      B,A
; --- Star 3: draw at new position ---
                LD      A,(star3_row)
                LD      C,B
                CALL    calc_vram
                CALL    set_cursor
                LD      A,STAR_BYTE_TOP
                CALL    write_byte
                CALL    next_row
                CALL    set_cursor
                LD      A,STAR_BYTE_BOT
                CALL    write_byte

; --- Heart 0: draw or erase at row 0 (needs lives >= 1) ---
                LD      A,(lives)
                CP      1
                JR      NC,h0_full      ; lives >= 1: draw full
                LD      A,0             ; heart_row = 0
                LD      C,HEART_COL
                CALL    calc_vram
                LD      B,8
                CALL    erase_rows
                JR      h0_done
h0_full:
                LD      A,0
                LD      C,HEART_COL
                CALL    calc_vram
                LD      HL,heart_sprite
                LD      B,8
                CALL    draw_sprite
h0_done:

; --- Heart 1: draw or erase at row 8 (needs lives >= 2) ---
                LD      A,(lives)
                CP      2
                JR      NC,h1_full
                LD      A,8
                LD      C,HEART_COL
                CALL    calc_vram
                LD      B,8
                CALL    erase_rows
                JR      h1_done
h1_full:
                LD      A,8
                LD      C,HEART_COL
                CALL    calc_vram
                LD      HL,heart_sprite
                LD      B,8
                CALL    draw_sprite
h1_done:

; --- Heart 2: draw or erase at row 16 (needs lives >= 3) ---
                LD      A,(lives)
                CP      3
                JR      NC,h2_full
                LD      A,16
                LD      C,HEART_COL
                CALL    calc_vram
                LD      B,8
                CALL    erase_rows
                JR      h2_done
h2_full:
                LD      A,16
                LD      C,HEART_COL
                CALL    calc_vram
                LD      HL,heart_sprite
                LD      B,8
                CALL    draw_sprite
h2_done:

; --- Save ship_row -> old_row ---
                LD      A,(ship_row)
                LD      (old_row),A

; --- Key poll: BDOS fn 0BH (returns A=0xFF if key available) ---
                LD      C,0BH
                CALL    BDOS
                AND     A               ; test A
                JR      Z,no_key        ; zero -> no key

; --- Key read: BDOS fn 06H, E=FFH (read key, no echo) ---
                LD      C,06H
                LD      E,0FFH
                CALL    BDOS

                CP      KEY_ESC
                JR      NZ,not_esc
                RET                     ; ESC -> exit to BASIC

not_esc:
                OR      KEY_SPACE       ; force bit 5 (lowercase -> uppercase range)
                CP      KEY_SPACE
                JR      Z,fire_shot
                CP      KEY_A
                JR      Z,ship_up
                CP      KEY_Z
                JR      Z,ship_down
                JR      no_key

ship_up:
                LD      A,(ship_row)
                SUB     SHIP_SPEED      ; move up (lower row number)
                JR      NC,ship_store
                XOR     A               ; clamp to 0
                JR      ship_store

ship_down:
                LD      A,(ship_row)
                ADD     A,SHIP_SPEED    ; move down (higher row number)
                CP      MAX_ROW+1
                JR      C,ship_store
                LD      A,MAX_ROW       ; clamp to MAX_ROW

ship_store:
                LD      (ship_row),A
                JR      no_key

fire_shot:
                LD      A,(shot_active)
                OR      A
                JR      NZ,no_key       ; already a shot in flight
                LD      A,SHIP_COL+1    ; shot starts one column right of ship
                LD      (shot_col),A
                LD      A,(ship_row)
                ADD     A,3             ; shot vertically centred on ship
                LD      (shot_row),A
                LD      A,1
                LD      (shot_active),A
                ; event_code = 1 (laser fired)
                LD      A,1
                LD      (event_code),A

no_key:

; --- Ship update: erase and redraw only if row changed ---
                LD      A,(old_row)
                LD      B,A             ; B = old_row
                LD      A,(ship_row)
                CP      B               ; same as before?
                JR      Z,after_ship_move

                LD      A,B             ; erase at old_row
                LD      C,SHIP_COL
                CALL    calc_vram
                LD      B,SHIP_HEIGHT
                CALL    erase_rows

                LD      A,(ship_row)    ; draw at new row
                LD      C,SHIP_COL
                CALL    calc_vram
                LD      HL,ship_sprite
                LD      B,SHIP_HEIGHT
                CALL    draw_sprite

after_ship_move:

; --- Projectile update ---
                LD      A,(shot_active)
                OR      A
                JR      Z,skip_shot     ; no shot -> skip

                ; erase shot at current position
                LD      A,(shot_col)
                LD      B,A
                LD      A,(shot_row)
                LD      C,B
                CALL    calc_vram
                CALL    set_cursor
                XOR     A
                CALL    write_byte
                CALL    next_row
                CALL    set_cursor
                XOR     A
                CALL    write_byte

                ; advance shot one column right
                LD      A,(shot_col)
                INC     A
                CP      MAX_COL+1       ; past right edge?
                JR      C,shot_store
                XOR     A               ; deactivate
                LD      (shot_active),A
                JR      skip_shot

shot_store:
                LD      (shot_col),A
                LD      B,A             ; B = new col

                ; draw shot at new position
                LD      A,(shot_row)
                LD      C,B
                CALL    calc_vram
                CALL    set_cursor
                LD      A,SHOT_BYTE_TOP
                CALL    write_byte
                CALL    next_row
                CALL    set_cursor
                LD      A,SHOT_BYTE_BOT
                CALL    write_byte

skip_shot:

; ============================================================
;  COLLISION CHECK: shot vs enemy 1
; ============================================================
                LD      A,(shot_active)
                OR      A
                JR      Z,try_e2_coll   ; no shot -> try enemy2

                LD      A,(enemy1_active)
                OR      A
                JR      Z,try_e2_coll   ; enemy1 not active

                ; same column?
                LD      A,(shot_col)
                LD      B,A
                LD      A,(enemy1_col)
                CP      B
                JR      NZ,try_e2_coll

                ; row overlap? shot_row - enemy1_row < 8
                LD      A,(shot_row)
                LD      B,A
                LD      A,(enemy1_row)
                LD      C,A
                LD      A,B             ; A = shot_row
                SUB     C               ; A = shot_row - enemy1_row (carry = enemy above)
                CP      8               ; if >= 8 (or wrapped), not a hit
                JR      NC,try_e2_coll  ; miss

                ; --- HIT enemy 1: erase shot ---
                LD      A,(shot_col)
                LD      B,A
                LD      A,(shot_row)
                LD      C,B
                CALL    calc_vram
                CALL    set_cursor
                XOR     A
                CALL    write_byte
                CALL    next_row
                CALL    set_cursor
                XOR     A
                CALL    write_byte
                XOR     A
                LD      (shot_active),A

                ; erase and deactivate enemy1
                LD      A,(enemy1_col)
                LD      B,A
                LD      A,(enemy1_row)
                LD      C,B
                CALL    calc_vram
                LD      B,ENEMY_HEIGHT
                CALL    erase_rows
                XOR     A
                LD      (enemy1_active),A

                CALL    hit_count_up
                LD      A,2
                LD      (event_code),A
                JP      after_enemy1

; ============================================================
;  COLLISION CHECK: shot vs enemy 2
; ============================================================
try_e2_coll:
                LD      A,(shot_active)
                OR      A
                JR      Z,no_collision

                LD      A,(enemy2_active)
                OR      A
                JR      Z,no_collision

                ; same column?
                LD      A,(shot_col)
                LD      B,A
                LD      A,(enemy2_col)
                CP      B
                JR      NZ,no_collision

                ; row overlap?
                LD      A,(shot_row)
                LD      B,A
                LD      A,(enemy2_row)
                LD      C,A
                LD      A,B
                SUB     C               ; shot_row - enemy2_row
                CP      8
                JR      NC,no_collision

                ; --- HIT enemy 2: erase shot ---
                LD      A,(shot_col)
                LD      B,A
                LD      A,(shot_row)
                LD      C,B
                CALL    calc_vram
                CALL    set_cursor
                XOR     A
                CALL    write_byte
                CALL    next_row
                CALL    set_cursor
                XOR     A
                CALL    write_byte
                XOR     A
                LD      (shot_active),A

                ; erase and deactivate enemy2
                LD      A,(enemy2_col)
                LD      B,A
                LD      A,(enemy2_row)
                LD      C,B
                CALL    calc_vram
                LD      B,ENEMY_HEIGHT
                CALL    erase_rows
                XOR     A
                LD      (enemy2_active),A

                CALL    hit_count_up
                LD      A,2
                LD      (event_code),A
                JP      after_enemy2

; ============================================================
;  NO SHOT COLLISION: redraw ship, check ship/enemy collisions
; ============================================================
no_collision:
                LD      A,(ship_row)
                LD      C,SHIP_COL
                CALL    calc_vram
                LD      HL,ship_sprite
                LD      B,SHIP_HEIGHT
                CALL    draw_sprite

; --- Ship/Enemy 1 collision ---
                LD      A,(enemy1_active)
                OR      A
                JR      Z,se1_miss      ; enemy1 not active

                LD      A,(enemy1_col)
                CP      SHIP_COL
                JR      NZ,se1_miss     ; not same column

                LD      A,(ship_row)
                LD      B,A             ; B = ship_row
                LD      A,(enemy1_row)
                LD      C,A             ; C = enemy1_row
                LD      A,B             ; A = ship_row
                SUB     C               ; A = ship_row - enemy1_row
                JR      C,se1_chk2      ; enemy above ship
                CP      8
                JR      NC,se1_miss     ; no overlap (gap >= 8)
                JR      se1_hit

se1_chk2:       ; enemy1_row > ship_row
                LD      A,C             ; A = enemy1_row
                SUB     B               ; A = enemy1_row - ship_row
                CP      8
                JR      NC,se1_miss

se1_hit:
                ; erase ship
                LD      A,(ship_row)
                LD      C,SHIP_COL
                CALL    calc_vram
                LD      B,SHIP_HEIGHT
                CALL    erase_rows
                ; erase enemy1
                LD      A,(enemy1_row)
                LD      C,SHIP_COL
                CALL    calc_vram
                LD      B,ENEMY_HEIGHT
                CALL    erase_rows
                XOR     A
                LD      (enemy1_active),A
                LD      A,1
                LD      (player_dead),A
                LD      A,3
                LD      (event_code),A
                RET                     ; return immediately to BASIC

se1_miss:

; --- Ship/Enemy 2 collision ---
                LD      A,(enemy2_active)
                OR      A
                JR      Z,se2_miss

                LD      A,(enemy2_col)
                CP      SHIP_COL
                JR      NZ,se2_miss

                LD      A,(ship_row)
                LD      B,A
                LD      A,(enemy2_row)
                LD      C,A
                LD      A,B
                SUB     C
                JR      C,se2_chk2
                CP      8
                JR      NC,se2_miss
                JR      se2_hit

se2_chk2:
                LD      A,C
                SUB     B
                CP      8
                JR      NC,se2_miss

se2_hit:
                LD      A,(ship_row)
                LD      C,SHIP_COL
                CALL    calc_vram
                LD      B,SHIP_HEIGHT
                CALL    erase_rows
                LD      A,(enemy2_row)
                LD      C,SHIP_COL
                CALL    calc_vram
                LD      B,ENEMY_HEIGHT
                CALL    erase_rows
                XOR     A
                LD      (enemy2_active),A
                LD      A,1
                LD      (player_dead),A
                LD      A,3
                LD      (event_code),A
                RET

se2_miss:

; ============================================================
;  ENEMY 1 UPDATE
; ============================================================
                LD      A,(enemy1_active)
                OR      A
                JR      Z,enemy1_spawn  ; not active -> spawn

                ; --- Move: erase at current position ---
                LD      A,(enemy1_col)
                LD      B,A
                LD      A,(enemy1_row)
                LD      C,B
                CALL    calc_vram
                LD      B,ENEMY_HEIGHT
                CALL    erase_rows

                ; --- Phase counter: only move every 4th frame ---
                LD      A,(enemy1_phase)
                INC     A
                AND     03H
                LD      (enemy1_phase),A
                OR      A
                JR      NZ,enemy1_draw  ; phase != 0: redraw without moving

                ; --- Horizontal: move left ---
                LD      A,(enemy1_col)
                OR      A
                JR      Z,enemy1_deact  ; reached left edge -> deactivate
                DEC     A
                LD      (enemy1_col),A

                ; --- Vertical: check direction ---
                LD      A,(enemy1_dy)
                CP      01H
                JR      Z,e1_down       ; dy=1 -> move down

                ; --- Moving up ---
                LD      A,(enemy1_row)
                OR      A
                JR      Z,e1_bnc_dn     ; at top -> bounce down
                DEC     A
                LD      (enemy1_row),A
                JR      enemy1_draw

e1_down:
                LD      A,(enemy1_row)
                CP      MAX_ROW
                JR      Z,e1_bnc_up     ; at bottom -> bounce up
                INC     A
                LD      (enemy1_row),A
                JR      enemy1_draw

e1_bnc_dn:
                LD      A,1
                LD      (enemy1_row),A
                LD      A,1
                LD      (enemy1_dy),A
                JR      enemy1_draw

e1_bnc_up:
                LD      A,MAX_ROW-1
                LD      (enemy1_row),A
                LD      A,0FFH
                LD      (enemy1_dy),A
                JR      enemy1_draw

enemy1_deact:
                XOR     A
                LD      (enemy1_active),A
                JR      after_enemy1

enemy1_spawn:
                ; Pseudo-random spawn: seed += 23, mask to 0-56 range
                LD      A,(rng_seed)
                ADD     A,17H
                LD      (rng_seed),A
                AND     38H             ; 0, 8, 16, 24, 32, 40, 48, 56
                LD      (enemy1_row),A
                LD      A,MAX_COL
                LD      (enemy1_col),A
                LD      A,1
                LD      (enemy1_active),A
                XOR     A
                LD      (enemy1_phase),A
                ; set initial direction from seed bit 0
                LD      A,(rng_seed)
                AND     01H
                JR      Z,e1_spwn_up
                LD      A,1
                LD      (enemy1_dy),A
                JR      enemy1_draw
e1_spwn_up:
                LD      A,0FFH
                LD      (enemy1_dy),A

enemy1_draw:
                LD      A,(enemy1_col)
                LD      B,A
                LD      A,(enemy1_row)
                LD      C,B
                CALL    calc_vram
                LD      HL,enemy_sprite
                LD      B,ENEMY_HEIGHT
                CALL    draw_sprite

after_enemy1:

; ============================================================
;  ENEMY 2 UPDATE (wave guard: only when wave=1)
; ============================================================
                LD      A,(wave)
                OR      A
                JP      Z,after_enemy2  ; wave=0 -> skip enemy2

                LD      A,(enemy2_active)
                OR      A
                JR      Z,enemy2_spawn

                ; --- Erase at current position ---
                LD      A,(enemy2_col)
                LD      B,A
                LD      A,(enemy2_row)
                LD      C,B
                CALL    calc_vram
                LD      B,ENEMY_HEIGHT
                CALL    erase_rows

                ; --- Phase counter ---
                LD      A,(enemy2_phase)
                INC     A
                AND     03H
                LD      (enemy2_phase),A
                OR      A
                JR      NZ,enemy2_draw

                ; --- Horizontal move left ---
                LD      A,(enemy2_col)
                OR      A
                JR      Z,enemy2_deact
                DEC     A
                LD      (enemy2_col),A

                ; --- Vertical: check direction ---
                LD      A,(enemy2_dy)
                CP      01H
                JR      Z,e2_down

                ; --- Moving up ---
                LD      A,(enemy2_row)
                OR      A
                JR      Z,e2_bnc_dn
                DEC     A
                LD      (enemy2_row),A
                JR      enemy2_draw

e2_down:
                LD      A,(enemy2_row)
                CP      MAX_ROW
                JR      Z,e2_bnc_up
                INC     A
                LD      (enemy2_row),A
                JR      enemy2_draw

e2_bnc_dn:
                LD      A,1
                LD      (enemy2_row),A
                LD      A,1
                LD      (enemy2_dy),A
                JR      enemy2_draw

e2_bnc_up:
                LD      A,MAX_ROW-1
                LD      (enemy2_row),A
                LD      A,0FFH
                LD      (enemy2_dy),A
                JR      enemy2_draw

enemy2_deact:
                XOR     A
                LD      (enemy2_active),A
                JR      after_enemy2

enemy2_spawn:
                ; seed += 29
                LD      A,(rng_seed)
                ADD     A,1DH
                LD      (rng_seed),A
                AND     38H
                LD      (enemy2_row),A
                LD      A,MAX_COL-4     ; spawn offset from enemy1
                LD      (enemy2_col),A
                LD      A,1
                LD      (enemy2_active),A
                XOR     A
                LD      (enemy2_phase),A
                LD      A,(rng_seed)
                AND     01H
                JR      Z,e2_spwn_up
                LD      A,1
                LD      (enemy2_dy),A
                JR      enemy2_draw
e2_spwn_up:
                LD      A,0FFH
                LD      (enemy2_dy),A

enemy2_draw:
                LD      A,(enemy2_col)
                LD      B,A
                LD      A,(enemy2_row)
                LD      C,B
                CALL    calc_vram
                LD      HL,enemy_sprite
                LD      B,ENEMY_HEIGHT
                CALL    draw_sprite

after_enemy2:

; --- Frame delay: LD HL,(frame_delay); loop DEC HL until zero ---
                LD      HL,(frame_delay)
delay_loop:
                DEC     HL
                LD      A,H
                OR      L
                JR      NZ,delay_loop

; --- End of frame: if event_code != 0, RET to BASIC for sound ---
                LD      A,(event_code)
                OR      A
                RET     NZ              ; BASIC dispatches on EV code

                JP      main_loop

; ============================================================
;  SUBROUTINES
; ============================================================

; hit_count_up: increment kill_count; if >= WAVE2_THRESHOLD set wave=1
hit_count_up:
                LD      A,(kill_count)
                INC     A
                LD      (kill_count),A
                CP      WAVE2_THRESHOLD
                RET     C               ; < threshold: return
                LD      A,1
                LD      (wave),A
                RET

; erase_rows: erase B rows starting at VRAM address in HL
; Preserves B count via PUSH/POP BC.
; On entry: HL=start VRAM addr, B=row count
erase_rows:
                PUSH    BC
                CALL    set_cursor
                XOR     A
                CALL    write_byte
                CALL    next_row
                POP     BC
                DJNZ    erase_rows
                RET

; draw_sprite: draw B rows from (HL) at VRAM address in HL (outer), sprite in HL (inner)
; On entry: HL=VRAM address (from calc_vram), HL also sprite pointer
; Note: on entry HL = calc_vram result (VRAM address); sprite pointer passed separately
; Actual call pattern: CALL calc_vram; LD HL,sprite_ptr; LD B,rows; CALL draw_sprite
; HL = sprite data pointer. set_cursor uses DE as VRAM addr (set by calc_vram via EB).
draw_sprite:
                PUSH    BC
                CALL    set_cursor
                LD      A,(HL)
                INC     HL
                CALL    write_byte
                PUSH    HL
                CALL    next_row
                POP     HL
                POP     BC
                DJNZ    draw_sprite
                RET

; next_row: advance DE (VRAM address) by 30 (one pixel row = 30 bytes wide)
; On entry: DE = current VRAM address
; On exit:  DE = address of next row (DE + 30)
next_row:
                LD      H,D
                LD      L,E
                LD      DE,001EH        ; 30 decimal
                ADD     HL,DE
                EX      DE,HL
                RET

; calc_vram: calculate VRAM byte address from row A and column C
; Formula: addr = C + (A * 30) ; because each row = 30 bytes
; On entry: A=row (0-63), C=column (0-29)
; On exit:  DE=VRAM address (0-1919)
; Method: addr = C + A*30 = C + A*(32-2) = C + A*32 - A*2
;         = C + (A<<5) - (A<<1)
;         HL = A*1 = A; HL = A*2 (<<1); push; HL = A*4; *8; *16; *32;
;         pop A*2; HL = A*32 - A*2 = A*30; add C -> HL = A*30+C
calc_vram:
                LD      L,A             ; HL = A (row)
                LD      H,00H
                ADD     HL,HL           ; HL = A*2
                PUSH    HL              ; save A*2
                ADD     HL,HL           ; HL = A*4
                ADD     HL,HL           ; HL = A*8
                ADD     HL,HL           ; HL = A*16
                ADD     HL,HL           ; HL = A*32
                POP     DE              ; DE = A*2
                OR      A               ; clear carry
                SBC     HL,DE           ; HL = A*30
                LD      E,C             ; E = col
                LD      D,00H
                ADD     HL,DE           ; HL = A*30 + col
                EX      DE,HL           ; DE = VRAM address
                RET

; set_cursor: set HD61830 cursor to VRAM address in DE
; Commands: 0AH (set cursor low byte), 0BH (set cursor high byte)
; LCD port 21H=command, 20H=data
set_cursor:
                CALL    wait_busy
                LD      A,0AH           ; Set Cursor Address (low)
                OUT     (LCD_CMD),A
                CALL    wait_busy
                LD      A,E             ; low byte of address
                OUT     (LCD_DATA),A
                CALL    wait_busy
                LD      A,0BH           ; Set Cursor Address (high)
                OUT     (LCD_CMD),A
                CALL    wait_busy
                LD      A,D             ; high byte of address
                OUT     (LCD_DATA),A
                RET

; write_byte: write A to HD61830 display RAM at current cursor
; Command: 0CH (Write Display RAM; cursor auto-increments)
write_byte:
                PUSH    AF
                CALL    wait_busy
                LD      A,0CH           ; Write Display RAM
                OUT     (LCD_CMD),A
                CALL    wait_busy
                POP     AF
                OUT     (LCD_DATA),A
                RET

; wait_busy: poll HD61830 status on port 21H until not busy
; Bit 7 of status = busy flag (1=busy). RLCA shifts bit7 into carry.
wait_busy:
                IN      A,(LCD_CMD)     ; read status
                RLCA                    ; bit7 -> carry
                JR      C,wait_busy     ; carry set -> busy, loop
                RET
