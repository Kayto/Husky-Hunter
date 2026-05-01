# SND4 — Z80 Machine Code Notes

See [../../ASM_README.md](../../ASM_README.md) for general workflow, assembler setup,
and the full index of worked examples.

## Files

| File | Description |
|---|---|
| `../SND4.BAS` | BASIC program (POKE loader + note loop) |
| `SND4.asm` | Z80 source (Intel-style, sjasmplus/Pasmo compatible) |
| `SND4.lst` | sjasmplus hex listing (addresses and bytes) |
| `SND4.dlst` | Decimal listing (for BASIC DATA transcription) |
| `POKE_LIST.txt` | DATA lines + address map formatted to match BAS |

## Program Summary

SND4 is a 35-byte machine code sound routine that replicates BASIC `SOUND`
using pure software bit-bang on port 86H (CD4099BE latch). Confirmed working
on hardware. Verified directly from ROM disassembly of the BASIC SOUND handler
at EPROM1:0x83CA.

| Property | Value |
|---|---|
| Binary size | 35 bytes |
| Load address | F605H = 62981 |
| CALL address | F605H = 62981 |
| Param base | F628H = 63016 (4 bytes) |
| Loader pattern | Simple POKE loop (`FOR I=0 TO 34:READ V:POKE 62981+I,V:NEXT I`) |

## How It Works

The ROM BASIC SOUND handler (EPROM1:0x83CA) generates sound by alternating
`OUT(86H),0` and `OUT(86H),1` with a delay loop between each transition.
The delay count equals the BASIC pitch argument; the number of full cycles
equals the duration argument. No timers or interrupts are involved.

SND4 replicates this exactly. Parameters are passed via POKE before CALL:

```basic
POKE 63016, pitch AND 255 : POKE 63017, INT(pitch/256)
POKE 63018, dur   AND 255 : POKE 63019, INT(dur/256)
X = CALL(62981)
```

This is equivalent to `SOUND pitch, dur`.

## Pitch Reference

| Note | Pitch |
|------|-------|
| A3   | 290   |
| A4   | 144   |
| B4   | 128   |
| C5   | 121   |
| D5   | 107   |
| E5   | 95    |
| F5   | 90    |
| G5   | 80    |
| A5   | 71    |

## ROM Evidence

- `OUT(86H)` — exactly 2 occurrences in the entire 1984 ROM, both at 0x83CA
- `OUT(02H)` — zero occurrences in the entire 1984 ROM
- NSC810 Port C is never used for sound generation
- Source: `Dev/Archive/ROM/rom_sound_truth.py` / `Dev/Sound_MC/rom_sound_truth.txt`
