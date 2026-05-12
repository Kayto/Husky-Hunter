# Progs/pong — Pong for the Husky Hunter

Two Pong games for the Husky Hunter. Both use Z80 machine code
embedded in Hunter BASIC for LCD rendering via the HD61830 at 240x64 pixels.

## 1P/ — Single-player

Human paddle on the left; ball bounces off the right wall.
File to transfer: `HBA/PONGGAME.HBA`

See [1P/README.md](1P/README.md) for controls, technical details and how to
rebuild from source.

## 2P/ — Human vs AI with scoring

Human paddle on the left, AI-controlled paddle on the right.
Scores displayed at top; delta-rendering for smooth frame rate.
File to transfer: `HBA/PONG2P.HBA`

See [2P/README.md](2P/README.md) for controls, difficulty settings and
technical details.
