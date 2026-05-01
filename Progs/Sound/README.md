# Sound Examples for the Husky Hunter

Sound exploration programs for the Husky Hunter (NSC800, 240×64 LCD).

- - -

## SOUND Command Reference

```
SOUND pitch, duration
```

* `pitch`: 1–65534 — **higher value = lower frequency**
* `duration`: 1–65534 — higher value = longer note
* Duration for \~1 second: `64130 / pitch`
* Four-octave range: pitch 493 (C, \~139 Hz) to pitch 28 (C, \~2092 Hz)

Key pitch values (from Appendix 9.13):

| Note | Freq (Hz) | Pitch |
| ---- | --------- | ----- |
| C (low) | 138.8 | 493 |
| C | 261.6 | 244 |
| C (mid) | 523.3 | 121 |
| G | 784.0 | 80 |
| C | 1046.5 | 59 |
| C (top) | 2092.0 | 28 |

`BEEP` — short single tone, equivalent to `OPCHR 7`.

- - -

## Files

| File | Description |
| ---- | ----------- |
| `SND1.BAS` | Scale & sweep — plays the 29-note four-octave scale ascending and descending, then continuous pitch sweeps |
| `SND2.BAS` | Tunes — Hunter manual example tune + Ode to Joy (two phrases, middle C octave) |
| `SND3.BAS` | FX sampler — interactive keyboard-triggered sound effects for Defend game development |
| `SND4.BAS` | MC sound — 35-byte machine code bit-bang routine at F605H; plays A4→A5 scale; confirmed working via port 86H (CD4099BE latch, ROM-verified) |
| `SND4_ASM/` | Assembly source, hex/decimal listings, and POKE reference for SND4 |

- - -

## SND1 — Scale & Sweep Demo

Exercises the full pitch range systematically.

1. **Ascending scale** — 29 notes from C (138 Hz) up to C (2092 Hz)
2. **Descending scale** — same notes reversed
3. **Ascending sweep** — continuous linear pitch sweep, low to high freq
4. **Descending sweep** — continuous sweep, high to low freq

Runs automatically. Press **ESC** to exit early.

- - -

## SND2 — Tunes Demo

Plays two short tunes back to back.

**Tune 1** — the example from the Hunter manual (page 298). Accelerating
multi-note pattern that demonstrates duration scaling with a loop counter.

**Tune 2** — Ode to Joy, two phrases, using middle-C octave pitch values.
Demonstrates: note duration variation (crotchet 350, dotted 525, minim 700),
RESTORE to re-point the DATA pointer, and pitch/duration READ pairs.

Press **ESC** to exit early.

- - -

## SND3 — Sound FX Sampler

Interactive sampler for Defend-game sound effects. Press keys to trigger:

| Key | Effect | Description |
| --- | ------ | ----------- |
| L | Laser | Fast descending freq sweep — "pew" shot sound |
| X | Explode | Low-freq burst sequence — enemy/player destroyed |
| A | Alarm | Alternating warble — wave start / incoming threat |
| P | Pickup | Rising C→E→G→C arpeggio — bonus/score collect |
| W | Win | Short fanfare C→D→E→G→C — wave complete |
| D | Death | Descending slide to low — player destroyed |
| ESC | Exit | Return to DEMOS |

Upper or lower case accepted.

- - -

## Usage

On the Husky Hunter:

```
BAS
LOAD "SND1"
RUN
```

Transfer `.HBA` versions via HCOM for direct DEMOS execution:

``` bash
python HBA_Format/hba_tokenize.py Progs/Sound/SND1.BAS Progs/Sound/SND1.HBA
python HBA_Format/hba_tokenize.py Progs/Sound/SND2.BAS Progs/Sound/SND2.HBA
python HBA_Format/hba_tokenize.py Progs/Sound/SND3.BAS Progs/Sound/SND3.HBA
python HBA_Format/hba_tokenize.py Progs/Sound/SND4.BAS Progs/Sound/SND4.HBA
```

- - -

## SND4 — Machine Code Sound (Port 86H)

35-byte MC routine that replicates `SOUND pitch, dur` from machine code.
Confirmed working on hardware. Verified directly from ROM disassembly of the
BASIC SOUND handler at EPROM1:0x83CA.

* Load MC bytes once via POKE loop (DATA lines 900–902)
* Before each note: `POKE 63016/63017` = pitch word, `POKE 63018/63019` = duration word
* Call with `X = CALL(62981)`
* Pitch/duration values are identical to `BASIC SOUND n,d`

See `SND4_ASM/ASM_README.md` for full assembly listing and address map.

- - -

## Notes for DefendERR Integration

The SND3 effects were designed for direct transplant into the DefendERR BASIC
loader as GOSUB routines. Each effect using a self-contained subroutine with
no shared variables. However given the sequential  delay overhead needed to produce the sound to end (as well as using BASIC), then these sounds were trimmed for the current preview so as not to interfere with the screen draws.

For MC-driven sound (faster, no BASIC overhead), the intent is to use the SND4 pattern:
load the 35-byte routine once, then POKE pitch/duration and `CALL(62981)`
for each note. The MC routine returns immediately. However similarily the actual time needed to produce the sound will likely not have any major benefit over the SND3 implementation.
Time will tell!

Sound effects trigger from BASIC around the MC game loop using `GOSUB` after
the `CALL` returns with a status flag in the return variable (e.g. `Z=CALL(AD)`).
Status codes can be checked with `POKE`/`PEEK` on a shared param block address.

Pitch param reminder: higher pitch number = lower frequency.

* Laser: low pitch# (high freq) sweeping up to higher pitch# (lower freq)
* Explosion: pitch 300–490 range (heavy, slow-sounding)
* Alarm warble: pitches 63 and 90 alternating

- - -

*By kayto April 2026 — Husky Hunter (NSC800, 240×64 LCD)*