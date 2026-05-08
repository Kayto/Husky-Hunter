#!/usr/bin/env python3
"""gen_defend_splash.py - Generate Defend.BAS splash screen using MC LCD blast.
By Kayto April 2026
Licensed under the MIT License. See LICENSE file for details.

Defend.BAS - Title splash screen, chains to DEFDAT1.
  - PNG converted to 1920 LSB-left bytes at build time
  - MC routine (58 bytes code + 1920 image bytes) loaded via POKE loop
  - MC: sets HD61830 cursor to (0,0), blasts all 1920 bytes via OUT
    using the same wait_busy/write-data pattern as the game MC.
    Much faster than BASIC DIO FOR loop.
  - Immediately chains: RUN "DEFDAT1" (no keypress)
  - DefDat1 line 5 is CUROFF only, so splash image persists on LCD
    during DefDat1's POKE/patch startup phase.

MC layout (offsets from AD):
    0  .. 57  : code (set_cursor_00 + blast_loop + wait_busy)
    58 .. 1977: 1920 image bytes (data_start)

Output:
    Dev/defender/PreRelease/Defend.BAS
    Dev/defender/PreRelease/Defend.HBA

Usage:
    python Dev/defender/gen_defend_splash.py
"""

from pathlib import Path
import subprocess
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow required: pip install Pillow")

LCD_W, LCD_H = 240, 64

SPLASH_PNG   = Path("Dev/defender/Images/SPLASH Apr 24, 2026, 10_03_28 AM.png")
CHAIN_TARGET = "DEFDAT1"
OUT_BAS      = Path("Progs/DefendERR/Defend.BAS")
OUT_HBA      = Path("HBA/DEFEND.HBA")

INVERT = False   # False: black pixels = lit dot (dark art on white bg)


# ---------------------------------------------------------------------------
# Minimal Z80 assembler
# ---------------------------------------------------------------------------

class Asm:
    def __init__(self):
        self.code = []
        self.labels = {}
        self.patches = []
        self.abs_patches = []

    def label(self, name):
        self.labels[name] = len(self.code)

    def emit(self, *bytes_):
        for b in bytes_:
            self.code.append(b & 0xFF)

    def emit_jr_cc(self, cc_byte, label):
        self.patches.append((len(self.code) + 1, label, 'jr'))
        self.emit(cc_byte, 0x00)

    def emit_call(self, label):
        off = len(self.code) + 1
        self.patches.append((off, label, 'abs'))
        self.abs_patches.append(off)
        self.emit(0xCD, 0x00, 0x00)

    def resolve(self):
        for offset, label, ptype in self.patches:
            if label not in self.labels:
                raise ValueError(f"Undefined label: {label}")
            target = self.labels[label]
            if ptype == 'jr':
                disp = target - (offset + 1)
                if disp < -128 or disp > 127:
                    raise ValueError(f"JR out of range to {label}: {disp}")
                self.code[offset] = disp & 0xFF
            elif ptype == 'abs':
                self.code[offset] = target & 0xFF
                self.code[offset + 1] = (target >> 8) & 0xFF

    def size(self):
        return len(self.code)

    def bytes(self):
        return list(self.code)


# ---------------------------------------------------------------------------
# PNG -> LCD bytes
# ---------------------------------------------------------------------------

def png_to_lcd_bytes(path: Path, invert: bool) -> list[int]:
    """Convert PNG to 1920 LSB-left bytes for HD61830."""
    img = Image.open(path).convert("L")
    src_ratio = img.width / img.height
    dst_ratio = LCD_W / LCD_H
    if src_ratio > dst_ratio:
        new_w = int(img.height * dst_ratio)
        off = (img.width - new_w) // 2
        img = img.crop((off, 0, off + new_w, img.height))
    else:
        new_h = int(img.width / dst_ratio)
        off = (img.height - new_h) // 2
        img = img.crop((0, off, img.width, off + new_h))
    img = img.resize((LCD_W, LCD_H), Image.LANCZOS)
    img = img.point(lambda x: 255 if x >= 160 else 0, '1')
    pixels = img.load()
    result = []
    for y in range(LCD_H):
        for bx in range(30):
            byte = 0
            for bit in range(8):
                px = bx * 8 + bit
                if px < LCD_W:
                    val = pixels[px, y]
                    lit = (val != 0) if invert else (val == 0)
                    if lit:
                        byte |= (1 << bit)
            result.append(byte)
    return result


# ---------------------------------------------------------------------------
# MC routine: set HD61830 cursor (0,0) then blast 1920 bytes
# ---------------------------------------------------------------------------

def build_mc(lcd_bytes: list[int]) -> Asm:
    a = Asm()

    # Set cursor X = 0
    a.emit_call('wait_busy')
    a.emit(0x3E, 0x0A)          # LD A, 0x0A  (set X address command)
    a.emit(0xD3, 0x21)          # OUT (0x21), A
    a.emit_call('wait_busy')
    a.emit(0xAF)                 # XOR A  (X = 0)
    a.emit(0xD3, 0x20)          # OUT (0x20), A

    # Set cursor Y = 0
    a.emit_call('wait_busy')
    a.emit(0x3E, 0x0B)          # LD A, 0x0B  (set Y address command)
    a.emit(0xD3, 0x21)          # OUT (0x21), A
    a.emit_call('wait_busy')
    a.emit(0xAF)                 # XOR A  (Y = 0)
    a.emit(0xD3, 0x20)          # OUT (0x20), A

    # LD HL, data_start  (absolute address, patched by BASIC)
    hl_off = len(a.code) + 1
    a.patches.append((hl_off, 'data_start', 'abs'))
    a.abs_patches.append(hl_off)
    a.emit(0x21, 0x00, 0x00)    # LD HL, data_start

    # LD BC, 1920
    a.emit(0x01, 0x80, 0x07)    # LD BC, 0x0780

    # Blast loop
    a.label('loop')
    a.emit_call('wait_busy')
    a.emit(0x3E, 0x0C)          # LD A, 0x0C  (write display data command)
    a.emit(0xD3, 0x21)          # OUT (0x21), A
    a.emit_call('wait_busy')
    a.emit(0x7E)                 # LD A, (HL)
    a.emit(0x23)                 # INC HL
    a.emit(0xD3, 0x20)          # OUT (0x20), A
    a.emit(0x0B)                 # DEC BC
    a.emit(0x78)                 # LD A, B
    a.emit(0xB1)                 # OR C
    a.emit_jr_cc(0x20, 'loop')  # JR NZ, loop
    a.emit(0xC9)                 # RET

    # wait_busy subroutine
    a.label('wait_busy')
    a.emit(0xDB, 0x21)          # IN A, (0x21)
    a.emit(0x07)                 # RLCA  (bit7 busy -> carry)
    a.emit(0x38, 0xFB)          # JR C, wait_busy
    a.emit(0xC9)                 # RET

    # Image data embedded immediately after code
    a.label('data_start')
    for b in lcd_bytes:
        a.emit(b)

    a.resolve()
    return a


# ---------------------------------------------------------------------------
# BASIC generator
# ---------------------------------------------------------------------------

def main():
    if not SPLASH_PNG.exists():
        sys.exit(f"Splash PNG not found: {SPLASH_PNG}")

    OUT_HBA.parent.mkdir(parents=True, exist_ok=True)

    lcd_bytes = png_to_lcd_bytes(SPLASH_PNG, INVERT)
    assert len(lcd_bytes) == 1920

    asm = build_mc(lcd_bytes)
    mc_bytes = asm.bytes()
    mc_len = len(mc_bytes)
    patch_offsets = asm.abs_patches
    code_len = asm.labels['data_start']

    print(f"MC splash: {mc_len} bytes ({code_len} code + 1920 image), {len(patch_offsets)} patches")

    n = mc_len if mc_len % 2 == 0 else mc_len + 1
    dim_d = (n // 2) - 1

    out = []
    out.append("1 REM Defend - Title splash screen")
    out.append("2 REM MC blast to HD61830 (fast)")
    out.append(f"3 REM Chains to {CHAIN_TARGET}")
    out.append("4 REM By kayto April 2026")
    out.append("5 CUROFF:SCREEN 1")
    out.append(f"6 DIM MC$({dim_d},1)")
    out.append("7 AD=VARPTR(MC$)-1")
    out.append(f"8 FOR I=0 TO {mc_len - 1}:READ V:POKE AD+I,V:NEXT I")
    out.append(f"9 FOR I=0 TO {len(patch_offsets) - 1}:READ P")
    out.append("10 L=PEEK(AD+P):H=PEEK(AD+P+1):W=L+H*256+AD")
    out.append("11 POKE AD+P,W-INT(W/256)*256:POKE AD+P+1,INT(W/256):NEXT I")
    out.append("15 Z=CALL(AD)")
    out.append(f'16 RUN "{CHAIN_TARGET}"')

    # MC code + embedded image data
    ln = 1000
    per_line = 15
    for i in range(0, len(mc_bytes), per_line):
        chunk = mc_bytes[i:i + per_line]
        out.append(f"{ln} DATA {','.join(str(b) for b in chunk)}")
        ln += 1

    # Patch offset table
    per_line = 16
    for i in range(0, len(patch_offsets), per_line):
        chunk = patch_offsets[i:i + per_line]
        out.append(f"{ln} DATA {','.join(str(p) for p in chunk)}")
        ln += 1

    OUT_BAS.write_text("\n".join(out) + "\n")
    print(f"Wrote {OUT_BAS} ({len(out)} lines)")

    result = subprocess.run(
        [sys.executable, "HBA_Format/hba_tokenize.py",
         str(OUT_BAS), str(OUT_HBA)],
        capture_output=True, text=True
    )
    print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())


if __name__ == "__main__":
    main()
