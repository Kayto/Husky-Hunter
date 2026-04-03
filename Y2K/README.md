# Y2K Date Handling on the Husky Hunter

The Hunter's ROM was written in 1983–84 and `DATE$` assumes a `19xx` century. Running in 2026 it returns `04-01-1926`. This document covers the workarounds.

All Y2K fixes here are by **Nicola Cowie** — both the BASIC `DATE$` workaround and the discovery of the undocumented century word at `0FA8Bh`.

## How the Hunter Stores Dates

The **MM58174A** RTC chip has no year register. The year is held in battery-backed RAM as two BCD digits:

| Dec | Hex | Name | Content |
|-----|------|------|---------|
| 63471 | F7EF | UNITDAY | Units of days |
| 63472 | F7F0 | TENDAY | Tens of days |
| 63473 | F7F1 | UNITMTH | Units of months |
| 63474 | F7F2 | TENMTH | Tens of months |
| 63475 | F7F3 | UNITYR | Units of years |
| 63476 | F7F4 | TENYR | Tens of years |

Full clock buffer runs F7E8–F7F4 (tenths-of-seconds through years). The CLCK system command sets date and time but **not the day-of-week** — use `DAY$` for that. The two-digit year wraps 99 → 00 correctly.

## The DATE$ Problem

From the manual (§5.5.2): *"the year defaulted to 19yy"*. The ROM prepends `"19"` unconditionally, so year `26` displays as `1926`.

Nicola Cowie found that setting DATE$ with a 4-digit year corrects the display. This uses a BAS one liner:

``` basic
DATE$=LEFT$(DATE$,6)+"2026"
```

**Confirmed on hardware.** The fix persists across BAS ↔ DEMOS switches and `NEW` — only lost on **power off**. `TIME$` and `DAY$` are unaffected.

## The Better Fix — Patching the Century Word

Nicola Cowie discovered that the ROM stores the default century as a **16-bit word** (ASCII `"19"` = `3139h`) at **RAM address `0FA8Bh`** during power-up. This is the value used by the system in both DEMOS and BASIC.

Overwriting this word with `3230h` (ASCII `"20"`) gives the correct century immediately:

```asm
start:  ld  bc, 3230h       ; ASCII "20" (B='2', C='0')
        ld  hl, 0FA8Bh      ; Century word in RAM
        ld  (hl), c          ; Low byte  -> 0FA8Bh
        inc hl
        ld  (hl), b          ; High byte -> 0FA8Ch
        jp  0                ; Warm boot back to DEMOS
```

Assemble this as `Y.COM`. After power on, just type `Y` then Enter — correct date.

**This fix survives warm restarts.** It only needs re-running after a full power cycle.

> **Note:** Location `0FA8Bh` is undocumented and may differ on OS versions other than `9G06h`.

## Summary

| Function | Status | Notes |
|----------|--------|-------|
| `DATE$` (read) | **19xx only** | ROM prepends `19` |
| `DATE$` (set 4-digit) | **Volatile** | Persists across BAS/DEMOS switches — lost on power off |
| Century word patch | **Semi-persistent** | Survives warm restart — lost on power off only |
| `TIME$` | OK | No year component |
| `DAY$` | OK | No year component — not set by CLCK |

## Files

| File | Description |
|------|-------------|
| `Y.COM` | Ready-to-run 12-byte DEMOS binary — copy to Hunter and type `Y` after power on. By Nicola Cowie |
| `Y2KFIX.ASM` | Z80 assembly source for `Y.COM` — patches century word at `0FA8Bh` to `"20"`. By Nicola Cowie |
| `Y2KFIX.HBA` | BASIC fix — patches DATE$ to 2026, shows before/after. **Lost on power off only.** By Nicola Cowie |
| `DAYSET.HBA` | Day-of-week setter — pick Mon–Sun. **Persistent — run once.** |

## References

- Husky Hunter Manual V09F, September 1984 — §3.4.3.2 (CLCK), §5.5.2 (DATE$), §9.7 (memory map)
- National Semiconductor MM58174A datasheet
- Nicola Cowie — Y2K DATE$ fix and century word discovery — [Facebook post](https://www.facebook.com/groups/118910608126229/permalink/27592395430351043/)
