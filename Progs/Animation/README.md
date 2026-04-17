# "Sprite" Animation Demos

Machine-code animated "sprites" for the Husky Hunter LCD display. Press any key to exit.

## Programs

### "SPRITE" — Horizontal Movement

An 8×8 ball moves horizontally across the screen at a fixed vertical position (row 28).

### BOUNCE — Wave Motion

An 8×8 ball moves horizontally with vertical sine-wave motion. The Y position is looked up from a 30-entry wave table (one per column) embedded in the MC. The ball traces a smooth sine curve as it crosses the screen, wrapping seamlessly.

### BOUNCE2 — Two-Sprite Wave

Two sprites follow the same sine wave in opposite directions — a circle moves right while a diamond moves left. They cross in the middle and pass through each other. Uses a shared `erase_at` subroutine to keep code compact.

### PONG — Bouncing Ball

A 4×4 ball bounces diagonally off all four screen edges. Moves 1 byte-column and 1 pixel-row per frame. Direction is reversed via `NEG` when hitting a wall. The ball sprite uses rounded corners (0x18, 0x3C, 0x3C, 0x18). Press any key to exit.

## Files

| File | Description |
|------|-------------|
| `gen_sprite.py` | Python generator — assembles Z80 MC and outputs `SPRITE.BAS` + `SPRITE.HBA` |
| `SPRITE.BAS` | BASIC listing — horizontal sprite loader |
| `SPRITE.HBA` | Tokenised version for transfer via HCOM |
| `gen_bounce.py` | Python generator — assembles Z80 MC and outputs `BOUNCE.BAS` + `BOUNCE.HBA` |
| `BOUNCE.BAS` | BASIC listing — wave-motion sprite loader |
| `BOUNCE.HBA` | Tokenised version for transfer via HCOM |
| `gen_bounce2.py` | Python generator — assembles Z80 MC and outputs `BOUNCE2.BAS` + `BOUNCE2.HBA` |
| `BOUNCE2.BAS` | BASIC listing — two-sprite wave loader |
| `BOUNCE2.HBA` | Tokenised version for transfer via HCOM |
| `gen_pong.py` | Python generator — assembles Z80 MC and outputs `PONG.BAS` + `PONG.HBA` |
| `PONG.BAS` | BASIC listing — bouncing ball loader |
| `PONG.HBA` | Tokenised version for transfer via HCOM |

## How It Works

BASIC loads MC and a parameter block into RAM, then hands control to MC with a single `CALL(62981)`. The entire animation loop runs in MC — BASIC is not re-entered until the user presses a key.

### Animation Loop (MC)

All programs share the same loop structure:

1. **Erase** — set cursor to current position, write zero bytes for 8 rows
2. **Update position** — increment column, wrap to 0 at column 30
3. **Draw** — set cursor to new position, write 8 sprite pattern bytes
4. **Delay** — countdown loop (configurable via parameter)
5. **Key check** — BDOS function 11 (console status); if no key, loop back to step 1

SPRITE uses a fixed VRAM base (row 28 × 30 = offset 840).
BOUNCE adds a `calc_vram` subroutine that looks up a row from a 30-entry sine wave table and computes `row × 30 + col` using the identity `row×30 = row×32 − row×2`.
BOUNCE2 doubles the erase/draw cycle for two sprites. The erase logic is factored into a shared `erase_at` subroutine. Sprite 1 increments its column (moves right) while sprite 2 decrements (moves left, wrapping 0→29).

### HD61830 LCD Interface

The Hunter's LCD is driven by a Hitachi HD61830 controller. Display VRAM is internal to the HD61830 and only accessible via I/O ports — it is not memory-mapped.

| Port | Function |
|------|----------|
| `0x21` | Command register / status read |
| `0x20` | Data register |

HD61830 commands used:
- `0x0A` — Set cursor address low byte
- `0x0B` — Set cursor address high byte
- `0x0C` — Write display data (auto-increments cursor)

Status bit 7 = busy flag, polled via `IN A,(0x21) / RLCA / JR C`.

### VRAM Layout

- 30 bytes per row × 64 rows = 1920 bytes total
- Each byte represents 8 horizontal pixels (LSB = leftmost)
- Row 28 × 30 = offset 840 is used as the vertical centre

## Memory Map

### SPRITE (140 bytes)

```
F605H (62981)  MC routine start (140 bytes)
F690H (63120)  MC routine end
               --- 175-byte gap ---
F740H (63296)  Parameter block
```

### BOUNCE (188 bytes)

```
F605H (62981)  MC routine start (158 bytes code)
F69DH (63133)  Subroutines end
F6A3H (63139)  Wave table (30 bytes, one Y-row per column)
F6C0H (63168)  MC routine end
               --- 127-byte gap ---
F740H (63296)  Parameter block
```

### BOUNCE2 (242 bytes)

```
F605H (62981)  MC routine start (212 bytes code + subroutines)
F6D9H (63193)  Wave table (30 bytes)
F6F6H (63222)  MC routine end
               --- 73-byte gap ---
F740H (63296)  Parameter block
```

### PONG (199 bytes)

```
F605H (62981)  MC routine start (199 bytes)
F6CCH (63180)  MC routine end
               --- 115-byte gap ---
F740H (63296)  Parameter block
```

### Parameter Block — SPRITE / BOUNCE

```
F740H  +0           Column position (0–29)
       +1..+8       Sprite pattern (8 bytes, one per row)
       +9,+10       Delay counter (little-endian word)
```

### Parameter Block — BOUNCE2

```
F740H  +0           Col1 — sprite 1 position (0–29, moves right)
       +1           Col2 — sprite 2 position (0–29, moves left)
       +2..+9       Sprite 1 data (8 bytes) — circle
       +10..+17     Sprite 2 data (8 bytes) — diamond
       +18,+19      Delay counter (little-endian word)
```

### Parameter Block — PONG

```
F740H  +0           Column position (byte column, 0–29)
       +1           Row position (pixel row, 0–60)
       +2           dx (direction: 1 or 0xFF = -1)
       +3           dy (direction: 1 or 0xFF = -1)
       +4..+7       Sprite pattern (4 bytes, one per row)
       +8,+9        Delay counter (little-endian word)
```

## Parameters

Edit the POKE lines in the `.BAS` file (or the constants in the generator) to adjust:

| Parameter | Default | Description |
|-----------|---------|-------------|
| Start column | 14 (SPRITE) / 0 (BOUNCE/BOUNCE2) | Initial horizontal position (0–29) |
| Sprite data | Circle (all) / Diamond (BOUNCE2 sprite 2) | 8 bytes defining each 8×8 sprite |
| Delay | 4000 | Frame delay — higher = slower |

BOUNCE also has wave parameters in `gen_bounce.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `WAVE_CENTRE` | 28 | Centre row of the wave |
| `WAVE_AMPLITUDE` | 20 | Rows above/below centre |
| `WAVE_PERIOD` | 30 | Columns per full cycle |

## Speed Control

Not a bug, its a feature. Holding **Shift + an arrow key** during the animation slows it down. Quite useful for debugging. I assume the firmware's keyboard interrupt handler consumes CPU cycles when scanning the key matrix and processing modifier keys.This reducing the time available for the animation loop.

## Building

Requires Python 3 and the HBA tokeniser. Run from the repo root:

```
python Dev/Animation/gen_sprite.py     # generates SPRITE.BAS + SPRITE.HBA
python Dev/Animation/gen_bounce.py     # generates BOUNCE.BAS + BOUNCE.HBA
python Dev/Animation/gen_bounce2.py    # generates BOUNCE2.BAS + BOUNCE2.HBA
python Dev/Animation/gen_pong.py       # generates PONG.BAS + PONG.HBA
```

## Running on the Hunter

1. Transfer the `.HBA` file to the Hunter using HCOM
2. `RUN "SPRITE"`, `RUN "BOUNCE"`, `RUN "BOUNCE2"`, or `RUN "PONG"`
3. Press any key to exit back to BASIC

## Known Issues

- **BOUNCE2**: Minor stray pixel artefacts occasionally appear near the centre of the screen on first run. The animation itself runs correctly. Possibly caused by residual VRAM data from `SCREEN 1` that the erase loop never reaches? An MC-based full VRAM clear was attempted but caused lockups — further investigation needed.

## Technical Notes

- Movement is **byte-aligned** (8-pixel steps) for simplicity — no sub-byte bit-shifting
- The sprite byte pattern `3C 7E FF FF FF FF 7E 3C` is a symmetric circle, identical under LSB-left or MSB-left interpretation
- MC subroutines (`set_cursor`, `write_byte`, `wait_busy`) only clobber the A register, preserving HL/DE/BC for the caller
- The `wait_busy` polling loop matches the ROM routine at `0x70AD`
- BOUNCE adds a `calc_vram` subroutine (27 bytes) and a 30-byte embedded wave table, bringing MC size from 140 to 188 bytes
- `calc_vram` uses `row×30 = row×32 − row×2` via shifts and `SBC HL,DE` — no multiply instruction needed
- The wave period equals the screen width (30 columns) so the animation wraps seamlessly
- BOUNCE2 adds a second sprite with a shared `erase_at` subroutine to avoid duplicating the erase loop, bringing MC size to 242 bytes
- BOUNCE2's diamond sprite pattern `18 3C 7E FF 7E 3C 18 00` is visually distinct from the circle
- PONG uses a 4×4 sprite instead of 8×8, with `NEG` (ED 44) to reverse direction on wall bounce — same erase/draw/delay/key-check loop structure as the other programs
- PONG bounds are col 0–29, row 0–60 (64 rows minus 4 sprite height)
