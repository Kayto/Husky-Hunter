# PONGGAME — Single-Player Pong for the Husky Hunter

A 4×4 ball bounces around the screen. Move the paddle to intercept it — miss and you'll hear a beep.

## Status

**v1.0 — Working.** Based on PONG7 development iteration (7 iterations, collision + beep).

## Controls

| Key | Action |
|-----|--------|
| A / a | Paddle up |
| Z / z | Paddle down |
| ESC | Exit |

## Gameplay

- **Ball:** 4×4 pixel sprite, bounces off all four walls
- **Paddle:** 12px tall at column 1 (left side), 8px wide
- **Net:** Solid 2-pixel centre line at column 15
- **Collision:** Ball bounces off paddle when vertically overlapping
- **Miss:** Ball passes through paddle and hits left wall — piezo beep sounds
- **Speed:** Adjustable via `BALL_DELAY` constant in `gen_ponggame.py`

## User Preferences

Edit these constants at the top of `gen_ponggame.py` then regenerate:

| Constant | Default | Description |
|----------|---------|-------------|
| `BALL_DELAY` | 10000 | Frame delay counter (higher = slower ball) |
| `PADDLE_SPEED` | 4 | Pixels moved per keypress |
| `PADDLE_HEIGHT` | 12 | Paddle height in pixel rows |
| `PADDLE_COL` | 1 | Paddle byte-column position |

## Technical Details

- **MC size:** 451 bytes (Z80 machine code)
- **Method:** MC stored in DIM array via VARPTR, patched at runtime
- **Parameters:** 12 bytes at fixed address F605H (62981)
- **LCD:** Direct HD61830 I/O with busy-checking
- **Input:** BDOS fn 11 (non-blocking status) + fn 6 (read key)

## Files

| File | Description |
|------|-------------|
| `gen_ponggame.py` | Python generator — assembles Z80 MC and outputs `PONGGAME.BAS` + `PONGGAME.HBA` |
| `PONGGAME.BAS` | BASIC listing — loads MC, draws net, runs game |
| `PONGGAME.HBA` | Tokenised version for transfer via HCOM |

## Usage

On the Husky Hunter:

1. Transfer `PONGGAME.HBA` to the Hunter via HCOM over RS-232
2. Enter `BAS`
3. `LOAD "PONGGAME"`
4. `RUN`
5. Use A/Z to move paddle, ESC to exit

## Build

From the repository root:

```bash
python Progs/pong/gen_ponggame.py
```

## Development Notes

Full development history (PONG through PONG7, 7 iterations) is documented in [Dev/pong/PONG_DEV.md](../../Dev/pong/PONG_DEV.md).
