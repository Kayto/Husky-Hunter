# Machine Code Programs

Hunter BASIC programs that embed and call Z80 machine code routines.

These programs demonstrate and test the Hunter BASIC machine code interface documented in manual §4.8.6. The technique allows BASIC programs to call CP/M BDOS functions and other Z80 routines that BASIC itself cannot access directly.

## The Interface (§4.8.6)

Machine code is written into RAM via `POKE` and executed via `CALL(address)`. The routine sits in memory for the lifetime of the program and can be called repeatedly — it behaves like a subroutine, not a one-shot loader.

### Storage locations

**User code area** (§9.7) — 50 bytes at `F605H`–`F655H` (decimal 62981–63061), reserved by the OS for user machine code. Simplest option: no `DIM`/`VARPTR` needed.

```basic
POKE 62981, byte1, byte2, ...
DEFSEG = 0
X = CALL(62981)
```

**String array** (§4.8.6.1) — for longer routines that exceed 50 bytes:

```basic
DIM MC$(D,1)           ' D = (num_bytes / 2) - 1
AD = VARPTR(MC$) - 1   ' address of first byte
POKE AD, byte1, ...
DEFSEG = 0
X = CALL(AD)
```

BASIC's string management leaves 2D string arrays alone, making the storage stable.

### Parameter passing

`P=ARG(N)` loads Z80 **E = N DIV 256** (high byte) and **C = N MOD 256** (low byte). `P` is a dummy variable — the return value is discarded. `ARG` as a standalone statement causes `*STX Error`.

For BDOS calls that only use C (function number) and E (single-byte parameter), `ARG+CALL(5)` is sufficient with no stub. For calls that need DE as a 16-bit address (file I/O fn 15/16/20), `ARG` cannot load D — a small stub is required to set `D=0` before the BDOS entry.

### Return value

`X = CALL(addr)` returns the Z80 A register value after the routine executes. Sufficient for BDOS success/error codes, character values, or single-byte results.

### DEFSEG

`DEFSEG = 0` must be set before any `CALL`. It selects the base memory segment. If any other code changes `DEFSEG`, reset it before the next `CALL`.

---

## Programs

### BDOSFN2.BAS — Console Output via BDOS

**Purpose:** Proof-of-concept for the BASIC↔machine code interface. Uses `ARG` and `CALL(5)` to invoke BDOS function 2 (Console Output) directly — no Z80 stub or POKE needed.

BDOS fn 2 needs C=2 (function) and E=ASCII character. `ARG(CH*256+2)` loads both in one call: E=CH (high byte), C=2 (low byte). Then `CALL(5)` hits BDOS directly.

**What it tests:**
- `DEFSEG = 0` before `CALL`
- `P=ARG(N)` syntax — dummy return variable, E=high byte, C=low byte
- `CALL(5)` — direct BDOS entry, no stub required
- `X=CALL()` return value (A register — unused for fn 2)
- Repeated calls (16× for "HELLO FROM BDOS" + CR/LF)

**No stub needed because:** fn 2 only uses C and E, both of which `ARG` loads directly. File I/O functions (fn 15/16/20) still need a stub to set D=0 for the FCB address in DE.

**Manual refs:** §4.8.6, §4.8.6.1, §3.5 (BDOS fn 2), §9.7

---

### COLLATMC.BAS — Collatz: BASIC vs Machine Code

**Purpose:** Side-by-side speed comparison of the Collatz conjecture sequence computed in interpreted BASIC versus a Z80 machine code subroutine called from BASIC. Both run the same seed and print step count + `TIME$` for comparison.

**What it demonstrates:**
- `POKE` installing a 33-byte Z80 routine into the user code area
- `P=ARG(N)` passing a 16-bit seed — E=high byte, C=low byte → routine reassembles as HL
- `S=CALL(62981)` returning step count in A register
- BASIC floating-point interpreter overhead vs native Z80 integer arithmetic

**Z80 routine (33 bytes at decimal 62981):**

```z80
LD H, E          ; seed high byte from ARG
LD L, C          ; seed low byte → HL = seed
LD B, 0          ; step counter
; loop:
LD A, H : OR A : JR NZ, not1
LD A, L : CP 1 : JR Z, done
; not1:
INC B            ; steps++
BIT 0, L         ; even/odd test
JR NZ, odd
; even:
SRL H : RR L     ; HL = HL / 2
JR loop
; odd:
PUSH HL : ADD HL, HL : POP DE : ADD HL, DE : INC HL  ; HL = 3*HL + 1
JR loop
; done:
LD A, B : RET    ; return step count
```

**Constraints:**
- 16-bit arithmetic: intermediate values must stay ≤ 65535 (no overflow detection)
- Step count returned in A register: must be ≤ 255
- Safe test seeds: 27 (111 steps, peak 9232), 97 (118 steps), 171 (124 steps)

**Comparison with [Progs/BASIC/COLLATZ.BAS](../BASIC/COLLATZ.BAS):** The BASIC version uses floating-point division + `INT()` for the even test and `3*N+1` via the interpreter — multiple tokens evaluated per step. The Z80 version uses `BIT 0,L` (single instruction) and register-pair shifts/adds. The speed difference should be dramatic on the 4 MHz NSC800.

**Known issue:** The BASIC elapsed time occasionally reads too high. The RTC buffer is refreshed via BDOS fn 48 before each PEEK sequence, but the BCD digit reads are not atomic! — i suspect the clock ticks on/between PEEKs so the result can be corrupt/inconsistent. Re-running the same seed usually gives the correct and more consistent value.

**Manual refs:** §4.8.6 (CALL/ARG), §9.7 (user code area)

---
