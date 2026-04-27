# Husky Hunter — LCD Control Reference

Low-level HD61830 LCD control for new BASIC and machine code development.

---

## Hardware Summary

The Hunter's display is a 240×64 monochrome LCD driven by a **Hitachi HD61830** LCD controller.

- **VRAM:** Internal to the HD61830 chip — **not in Z80 memory space**.
- **Access:** I/O ports only (`OUT`/`IN`, or `OUT (n),A` in Z80).
- **No paging required.** Writing directly to the HD61830 from BASIC or MC is safe and simple.

The firmware's `PSET` and `LINE` commands maintain a **shadow buffer** (in paged RAM) alongside
the HD61830 VRAM so that `POINT(x,y)` can read back pixel values. Direct `OUT`-based writes
bypass this shadow buffer — `POINT()` will return stale values after direct writes, but the
display updates correctly. This is fine for full-frame renders where readback is not needed.

---

## I/O Ports

| Port | Dec | Direction | Function |
|------|-----|-----------|---------|
| `20H` | 32 | Write | Data byte to current HD61830 command |
| `21H` | 33 | Write | Command register |
| `21H` | 33 | Read | Status (bit 7: 1 = busy, 0 = ready) |
| `3EH` | 62 | Read | VRAM data read (after `CMD_READ`, requires two reads; first is dummy) |

---

## Commands

| Cmd | Hex | Usage |
|-----|-----|-------|
| Set cursor addr low  | `0A` | `OUT 33,10 : OUT 32,lo_byte` |
| Set cursor addr high | `0B` | `OUT 33,11 : OUT 32,hi_byte` |
| Write display data   | `0C` | `OUT 33,12 : OUT 32,data_byte` — auto-increments cursor |
| Read display data    | `0D` | `OUT 33,13` — then read port `3EH` twice (first read is dummy) |

After every `CMD_WRITE` (`0C`) byte the HD61830 automatically increments its internal
cursor address. To write a full screen you only need to set the cursor once to address 0,
then issue 1920 consecutive write commands.

---

## VRAM Layout

The display is 240 pixels wide × 64 pixels tall, stored as 1920 bytes.
Each byte holds 8 horizontally adjacent pixels. There are 30 bytes per row (240 ÷ 8 = 30).

```
addr = row * 30 + col_byte      (row 0–63, col_byte 0–29)
Total: 1920 bytes
```

Address 0 = top-left 8 pixels. Address 1919 = bottom-right 8 pixels.

---

## Pixel Addressing

You have **full independent control over every pixel**. Any pixel (px, py) maps to a specific
bit within a specific VRAM byte:

```
col_byte  = px // 8          (which byte within the row, 0–29)
bit_mask  = 1 << (px % 8)    (which bit within that byte, LSB = leftmost)
vram_addr = py * 30 + col_byte
```

Because the HD61830 works in whole bytes, **setting or clearing a single pixel requires a
read-modify-write** — read the existing byte, OR/AND the bit mask, write back:

**BASIC — set one pixel at (px, py):**
```basic
A = py * 30 + INT(px / 8)             ' VRAM address
M = 2 ^ (px - INT(px / 8) * 8)        ' bit mask (LSB = leftmost)
OUT 33,13 : REM CMD_READ, then dummy read then real read
OUT 33,10 : OUT 32, A - INT(A/256)*256  ' set cursor
OUT 33,11 : OUT 32, INT(A/256)
OUT 33,13                               ' CMD_READ
V = INP(62) : V = INP(62)              ' first is dummy, second is data
OUT 33,10 : OUT 32, A - INT(A/256)*256  ' reposition cursor (read advanced it)
OUT 33,11 : OUT 32, INT(A/256)
OUT 33,12 : OUT 32, V OR M             ' CMD_WRITE with bit set
```

In practice, direct pixel manipulation from BASIC is slow. **For full-frame or large-area
writes, always write whole bytes** — pre-compute the pixel pattern into bytes and blast the
bytes sequentially. The read-modify-write is only needed when updating isolated pixels in a
scene where surrounding pixels must be preserved.

**MC — set one pixel, preserving neighbours:**
```z80
; Input: DE = VRAM address, B = bit mask (1 << (px % 8))
; Read current byte
    CALL wait_busy
    LD   A,0DH          ; CMD_READ
    OUT  (21H),A
    IN   A,(3EH)        ; dummy read
    IN   A,(3EH)        ; actual data
    OR   B              ; set target bit
; Reposition cursor (read auto-incremented it)
    CALL set_cursor     ; DE still = original address
; Write modified byte
    CALL write_byte     ; A = modified byte
```

**MC — clear one pixel:**
Same as above but `AND (NOT B)` — in Z80: `CPL` on B then `AND B`, or precompute the
inverted mask: `LD C,B / LD A,0FFH / XOR C` to get the AND mask, then `AND` with the
read-back value.

### Pixel-to-byte summary

| Pixel X range | col_byte | Bit positions (LSB=left) |
|---------------|----------|--------------------------|
| 0–7   | 0  | bit 0 = px 0, bit 7 = px 7 |
| 8–15  | 1  | bit 0 = px 8, bit 7 = px 15 |
| …     | …  | … |
| 232–239 | 29 | bit 0 = px 232, bit 7 = px 239 |

---

## Bit Order — LSB = leftmost pixel

The HD61830 uses **LSB = leftmost pixel** within each byte. This is the opposite of the
convention used by BASIC's PSET handler and `png2hba.py`.

Confirmed by `BITORD.BAS` on real hardware: writing `0x80` (MSB only) placed a dot at
pixel column 7, not pixel column 0. Writing `0x01` placed it at column 0.

| Byte value | Pixels set (columns within byte, left→right) |
|------------|----------------------------------------------|
| `0x01` | col 0 only |
| `0x80` | col 7 only |
| `0xFF` | all 8 columns |
| `0x0F` | cols 0–3 |

Images generated by `gen_imgdio.py` and `gen_imgmc.py` are **pre-bit-reversed** to account
for this — each source byte has its bit order flipped before output so the display is correct.

---

## Busy Flag

The HD61830 asserts bit 7 of port `21H` while processing a command. **From BASIC, busy polling
is unnecessary** — the interpreter overhead between consecutive `OUT` statements (~200 µs) far
exceeds the HD61830's busy time (~2 µs). Skip polling in BASIC for simplicity.

In **machine code**, always poll before each command and each data write:

```z80
wait_busy:
    IN   A,(21H)   ; read status
    RLCA           ; bit 7 → carry
    JR   C,wait_busy   ; loop while busy
```

---

## BASIC Patterns

### Position cursor

```basic
OUT 33,10:OUT 32,0    ' addr low = 0
OUT 33,11:OUT 32,0    ' addr high = 0
```

### Write one byte at cursor (cursor auto-increments)

```basic
OUT 33,12:OUT 32,V    ' write byte V to current cursor position
```

### Fill entire display with value V

```basic
OUT 33,10:OUT 32,0
OUT 33,11:OUT 32,0
FOR I=0 TO 1919:OUT 33,12:OUT 32,V:NEXT I
```

### Clear display

```basic
OUT 33,10:OUT 32,0
OUT 33,11:OUT 32,0
FOR I=0 TO 1919:OUT 33,12:OUT 32,0:NEXT I
```

### Write a full-screen image (bit-reversed DATA, 1920 bytes)

```basic
OUT 33,10:OUT 32,0
OUT 33,11:OUT 32,0
FOR I=0 TO 1919:READ V:OUT 33,12:OUT 32,V:NEXT I
```

No SCREEN 1 call is needed; the HD61830 is always active. Use `SCREEN 0` beforehand
to suppress the firmware's own screen output interfering with direct VRAM writes.

---

## Machine Code Pattern

See `image_writer/IMGMC_ASM/IMGMC.asm` for the canonical tight-loop blast routine (30 bytes).
It loads image data from a RAM buffer at `C000H` and writes all 1920 bytes to the HD61830
with busy polling inlined at both sites.

```z80
; Set HD61830 cursor to origin first (from BASIC before calling MC):
;   OUT 33,10:OUT 32,0 / OUT 33,11:OUT 32,0

blast_loop:
busy1:  IN  A,(21H)
        RLCA
        JR  C,busy1
        LD  A,0CH          ; CMD_WRITE
        OUT (21H),A
busy2:  IN  A,(21H)
        RLCA
        JR  C,busy2
        LD  A,(HL)
        OUT (20H),A
        INC HL
        DEC DE
        LD  A,D
        OR  E
        JR  NZ,blast_loop
        RET
```

**Timing**: ~13 ms for a full 1920-byte frame → ~77 fps theoretical, dominated by busy-wait overhead.

### Subroutine library — confirmed working on hardware

All animation and game programs share these subroutines. Copy verbatim.

#### `wait_busy` — poll HD61830 until ready

Clobbers: A. Matches ROM routine at 0x70AD.

```z80
wait_busy:
    IN   A,(21H)      ; read status port
    RLCA              ; bit 7 → carry
    JR   C,wait_busy  ; loop while busy
    RET
```

#### `set_cursor` — position HD61830 cursor

Input: DE = VRAM address (0–1919). Clobbers: A. Preserves: HL, DE, BC.

```z80
set_cursor:
    CALL wait_busy
    LD   A,0AH         ; CMD: cursor addr low
    OUT  (21H),A
    CALL wait_busy
    LD   A,E
    OUT  (20H),A       ; data: low byte
    CALL wait_busy
    LD   A,0BH         ; CMD: cursor addr high
    OUT  (21H),A
    CALL wait_busy
    LD   A,D
    OUT  (20H),A       ; data: high byte
    RET
```

#### `write_byte` — write data byte to current cursor position

Input: A = data byte. Cursor auto-increments after write. Clobbers: A. Preserves: HL, DE, BC.

```z80
write_byte:
    PUSH AF
    CALL wait_busy
    LD   A,0CH         ; CMD: write display data
    OUT  (21H),A
    CALL wait_busy
    POP  AF
    OUT  (20H),A       ; data byte
    RET
```

#### `calc_vram` — compute VRAM address from row and column

Input: A = pixel row (0–63), C = byte column (0–29). Output: DE = VRAM address. Clobbers: A, HL, DE, C. Preserves: B.

Uses the identity `row × 30 = row × 32 − row × 2` to avoid a multiply:

```z80
calc_vram:
    LD   L,A
    LD   H,0           ; HL = row
    ADD  HL,HL         ; row*2
    PUSH HL            ; save row*2
    ADD  HL,HL         ; row*4
    ADD  HL,HL         ; row*8
    ADD  HL,HL         ; row*16
    ADD  HL,HL         ; row*32
    POP  DE            ; DE = row*2
    OR   A             ; clear carry
    SBC  HL,DE         ; HL = row*30
    LD   E,C           ; E = col
    LD   D,0
    ADD  HL,DE         ; HL = row*30 + col
    EX   DE,HL         ; DE = VRAM addr
    RET
```

**Note:** `SBC HL,DE` (`ED 52`) and `NEG` (`ED 44`) are confirmed working on the NSC800. `LD BC,(nn)` (`ED 4B`) is unreliable — avoid it.

#### `next_row` — advance DE by 30 (one LCD row)

Clobbers: HL. Preserves: BC.

```z80
next_row:
    LD   H,D
    LD   L,E
    LD   DE,30
    ADD  HL,DE
    EX   DE,HL
    RET
```

#### `draw_rows` / `erase_rows` — write/clear a run of rows

Input: B = row count, DE = VRAM start address.

```z80
draw_rows:           ; write 0xFF to B consecutive rows
    PUSH BC
    CALL set_cursor
    LD   A,0FFH
    CALL write_byte
    CALL next_row
    POP  BC
    DJNZ draw_rows
    RET

erase_rows:          ; write 0x00 to B consecutive rows
    PUSH BC
    CALL set_cursor
    XOR  A
    CALL write_byte
    CALL next_row
    POP  BC
    DJNZ erase_rows
    RET
```

#### `draw_sprite` — write N rows from a data array

Input: B = row count, DE = VRAM start, HL = pointer to sprite data. Each call advances HL by one byte per row written. Clobbers: A. Preserves: BC (via push/pop).

Use this for variable sprite data; use `draw_rows` when the fill value is constant.

```z80
draw_sprite:
    PUSH BC
    CALL set_cursor
    LD   A,(HL)        ; fetch sprite byte
    INC  HL
    CALL write_byte
    PUSH HL
    CALL next_row      ; DE += 30
    POP  HL
    POP  BC
    DJNZ draw_sprite
    RET
```

---

## MC Animation Pattern — Erase / Update / Draw

The subroutines above are the building blocks. This section explains how they are combined
to produce movement, animation, and games.

### The frame loop

Every MC animation loop follows this sequence, run continuously until a key is pressed:

```
1. ERASE   — write 0x00 to each object's current VRAM position (removes it from screen)
2. UPDATE  — apply movement: increment/decrement position variables, wrap at boundaries
3. DRAW    — write sprite bytes to the new VRAM position (places each object at new location)
4. DELAY   — tight DEC HL / JR NZ loop to cap frame rate
5. KEY CHK — read keyboard; branch on result (see below)
6. JP      — back to step 1
```

The display shows each object at its new position for the duration of the delay. Because the
HD61830 has no vsync and no blanking, the erase → draw transition happens within
microseconds and is imperceptible at normal animation speeds.

**Step 5 — key check serves two roles:**

- **Exit**: `BDOS fn 11` returns A≠0 if any key is waiting; `RET` to BASIC. Used by demos
  that run autonomously until interrupted.

- **Game input**: a full game reads the actual key character (`BDOS fn 6` with E=FFH for
  non-blocking) and branches on the value to adjust position variables before the next
  erase/draw cycle. Left/right/up/down keys modify the player object's position; no key
  leaves it unchanged. The UPDATE step therefore reflects both autonomous object motion
  (ball, enemies) and the player's input from the previous frame — a game updates a
  player-controlled object each frame based on the key held, while autonomous objects
  update via their own direction variables.

### Position representation

Each object's position is stored as two integers in the MC parameter block:

- **col** — byte column (0–29). One unit = 8 pixels. This is the `col_byte` from the VRAM formula.
- **row** — display row (0–63). The *top* row of the sprite's bounding rectangle.

`calc_vram` converts (col, row) to a VRAM byte address: `DE = row × 30 + col`. Subsequent
rows of the sprite are `DE += 30` apart, advanced by `next_row`.

### Sprite height

A sprite is N rows tall. The erase and draw loops both run B = N iterations, advancing DE
by 30 per iteration via `next_row`. For an 8-row sprite: 8 × (set_cursor + write_byte +
next_row) per erase or draw pass.

### Horizontal movement (byte-aligned)

Movement is in whole byte column steps (8 px per step). The update step:

```z80
LD  A,(col)
INC A           ; move right one column (8 pixels)
CP  30
JR  C,no_wrap
XOR A           ; wrap to column 0
no_wrap:
LD  (col),A
```

For left movement, `DEC A` with wrap at 0 → 29.

**Sub-byte movement** (1 px steps) is not implemented in any current program. It requires
splitting the sprite across two adjacent column bytes and pre-shifting the sprite data:

```
left_byte  = sprite_data >> px_offset
right_byte = sprite_data << (8 - px_offset)
```

Both column bytes must be erased and redrawn each frame, doubling I/O cost per row.

### Vertical movement and lookup tables

For simple vertical movement, `row` is incremented or decremented like `col` above with
top/bottom boundary clamping or wrap.

For non-linear motion (wave, sine, pre-scripted paths), a **lookup table** is embedded in
MC as data bytes. Each frame, the current phase index selects the row value from the table.
`calc_vram` is then called with the looked-up row. This gives smooth motion with no runtime
arithmetic — all path values are computed at program-generation time and embedded as bytes.

### Multiple sprites

For N independent objects, the frame loop extends to:

```
ERASE all objects at old positions   ← all erases first
UPDATE all position variables
DRAW all objects at new positions    ← all draws after all erases
DELAY + KEY CHECK
```

All erases must happen before any draws. This prevents visual glitches when objects are
adjacent — you never draw one object while a neighbour is mid-erase.

### Collision detection

Collision is checked **between UPDATE and DRAW**, using position variables — never by
reading VRAM. The principle: if two objects' bounding rectangles overlap, they have
collided. Reverse the relevant direction variable (`NEG`) and the next draw places the
object on its corrected trajectory.

#### Wall / boundary bounce

After computing the new position, check if it is out of range and negate the direction:

```z80
; Horizontal wall bounce (col 0–29)
LD  A,(col)
LD  B,A
LD  A,(dx)        ; 1 or 0xFF (-1)
ADD A,B           ; tentative new col
CP  30
JR  C,col_ok      ; still in range
LD  A,(dx)
NEG               ; reverse: 1 → 0xFF or 0xFF → 1
LD  (dx),A
ADD A,B           ; recompute with reversed direction
col_ok:
LD  (col),A
```

The same pattern handles vertical bounce with `row`/`dy`/max_row.

#### Sprite–sprite collision

Three conditions must all be true:

1. **Same column** — `object_col == target_col`
2. **Moving toward the target** — direction variable check (e.g. `INC A / JR NZ` to test dx == 0xFF)
3. **Vertical overlap** — object bottom >= target top AND object top < target bottom

```z80
; Condition 3a: obj_bottom (row + height - 1) >= target_top?
LD  A,(target_row)
LD  B,A
LD  A,(obj_row)
ADD A,(obj_height - 1)
CP  B
JR  C,no_bounce     ; obj bottom < target top → no overlap

; Condition 3b: obj_top (row) < target_bottom (target_row + target_height)?
LD  A,(target_row)
ADD A,(target_height)
LD  B,A
LD  A,(obj_row)
CP  B
JR  NC,no_bounce    ; obj top >= target bottom → no overlap

; Overlap confirmed — reverse direction
LD  A,(dx)
NEG
LD  (dx),A
no_bounce:
```

#### Object–object collision (multiple enemies)

For multiple active objects, loop over each one's position entry and apply the same overlap
test. Mark hit objects inactive and erase them. Only active objects are drawn each frame.

#### Key principle

**Never use VRAM readback (`CMD_READ`, port 3EH) for collision.** Store the bounding
rectangle of each object in the parameter block and compare positions arithmetically.

### Frame rate

The delay loop count controls frame rate directly. Higher count = slower animation.
Typical values for visible smooth motion: 200–5000 iterations at 4 MHz. A count of 0
gives maximum speed (limited only by I/O overhead of the erase/draw passes).

---

## Existing Programs as Examples

| Program | Location | What it demonstrates |
|---------|----------|----------------------|
| `IMGDIO.BAS` | `Progs/image_writer/` | Full image render via BASIC `OUT` loop — no MC, no PSET. 25× faster than PSET baseline |
| `IMGMC.BAS` | `Progs/image_writer/` | MC-accelerated full-frame blast: loads buffer via POKE, fires MC to transfer all 1920 bytes at hardware speed (~13 ms) |
| `SPRITE.BAS` | `Progs/Animation/` | MC sprite: byte-aligned horizontal movement, fixed row. Erase-at-old / draw-at-new pattern. Standard `set_cursor`/`write_byte`/`wait_busy` subroutines |
| `BOUNCE.BAS` | `Progs/Animation/` | MC wave-motion sprite: ball follows a sine wave lookup table embedded in MC. `calc_vram` using row×32−row×2 trick |
| `BOUNCE2.BAS` | `Progs/Animation/` | Two independent wave-motion sprites moving in opposite directions |
| `PONGGAME.BAS` | `Progs/pong/` | Full game: PSET draws static net, MC handles ball + paddle with collision. Position-independent MC via `VARPTR`/`DIM` with runtime patch loop. `draw_rows`/`erase_rows`/`next_row` helpers |

---

## Performance Reference

| Method | Full frame time | Notes |
|--------|-----------------|-------|
| BASIC `PSET` per pixel | ~617 s | Baseline — firmware overhead per pixel |
| BASIC `LINE` hline runs | ~50 s | Pre-computed runs, `IMGHLIN.BAS` |
| BASIC `OUT` loop | ~25 s | Direct HD61830 write, no bit-unpack — `IMGDIO.BAS` |
| MC blast from RAM buffer | ~13 ms | `IMGMC.BAS` — BASIC fills buffer, MC blasts to LCD |

---

## Notes for New Development

- **Always enter `SCREEN 0`** before direct LCD writes. The firmware's graphics rasteriser
  runs on interrupts and will corrupt your writes if graphics mode is active.
- **SCREEN 1 is not required** for direct I/O output. You can write to the HD61830 from
  text mode and the pixels will appear.
- **The cursor wraps** from address 1919 back to 0. Writing more than 1920 bytes in a
  single pass overwrites from the beginning.
- **Do not write to I/O port `E0H`** (memory paging register) from BASIC or any non-atomic
  MC routine. This remaps OS workspace RAM and will lock the machine (requires battery pull).
  The firmware's `PSET` handler uses it safely with DI/EI in a 6-instruction window.
- **POINT() accuracy**: after direct `OUT` writes, `POINT(x,y)` reads the shadow buffer
  (not HD61830 VRAM) and will return 0 for pixels you wrote directly. If you need readback,
  use PSET/LINE, or maintain your own shadow array in BASIC.

---

## References

- `HARDWARE_README.md` — hardware overview including HD61830 command table
- `Progs/image_writer/IMGMC_ASM/IMGMC.asm` — MC blast routine source
- `Progs/image_writer/IMGMC_ASM/ASM_README.md` — MC blast assembly notes
- `Progs/Animation/gen_sprite.py`, `gen_bounce.py`, `gen_bounce2.py` — MC subroutine source (set_cursor, write_byte, calc_vram)
- `Progs/pong/gen_ponggame.py` — position-independent MC, VARPTR method, draw_rows/erase_rows
- Hitachi LM200 LCD module datasheet: `Docs/Hardware/LM200-Hitachi_copy.pdf` (gitignored — local copy only)
