# Husky Hunter — Programs for the 1983 Ruggedised Field Computer

Programs and tools for the **Husky Hunter** portable computer (NSC800-4 @ 4MHz, DEMOS 2.2 / CP/M 2.2, 240×64 LCD).

The focus for this repo is on Hunter BASIC (rather than the CP/M support) for the following reasons.

* Pixel level control of the LCD screen.
* Some interesting capability for sub routine links between BASIC and BDOS/Z80 Machine Code (rather than the more typical single shot loaders).
* Bidirectional RS-232 with per-character send/receive (`LOPCHR`, `LINCHR`) and event-driven interrupt handlers (`ON COM`, `ON COMMS`, `ON POWER`) — more field data-collection language than home-micro BASIC.

The <b>`HBA/`</b> folder contains pre-built tokenized binaries for all programs — transfer any `.HBA` file to the Hunter via HCOM and run it directly from the DEMOS prompt without any LOAD/SAVE step.

To convert your own `.BAS` source files, use the tools in [`HBA_Format/`](HBA_Format/README.md).

![Terrain profile on Husky Hunter](Progs/images/20260320_234803.jpg)
![Image on Husky Hunter](Progs/images/20260321_120202~2.jpg)
![Husky Hunter projects collage](Progs/images/collage.jpg)

## Hunter BASIC Programs

Programs that run on the Hunter. Source files are in `Progs/` and `Y2K/`; pre-built binaries are in [`HBA/`](HBA/).

| Program | Description | Status |
| ------- | ----------- | ------ |
| [Terrain](Progs/Terrain/) | Point-to-point radio link profiler — automatic terrain profile extraction from contour data, LOS overlay, dB path loss | Working on hardware |
| [Tide](Progs/Tide/) | Self-contained tidal predictor — computes and plots 24-hour tide curves from 7 harmonic constituents, 6 built-in UK ports | Working on hardware |
| [Morse](Progs/Morse/) | Morse code tape — type a message and watch it scroll across the LCD with audio output, ITU standard timing | Working on hardware |
| [news\_feed](Progs/news_feed/) | BBC News headline ticker — Hunter program displays headlines sent by PC feed over RS-232 | Working on hardware |
| [performance\_log](Progs/performance_log/) | Real-time PC performance display — Hunter program displays CPU/memory sent by PC feed over RS-232 | Working on hardware |
| [log\_file](Progs/log_file/) | Performance file logger — logs CPU and memory samples sent by PC feed over RS-232 to PERFLOG.DAT on the Hunter, with menu-driven readback | Working on hardware |
| [image\_writer](Progs/image_writer/) | LCD image display — Hunter program shows images converted from PNG/JPEG by PC-side tool | Working on hardware |
| [BASIC](Progs/BASIC/) | Short stand-alone programs — charset printer, Collatz sequence, Hello World graphic, system diagnostic | Working on hardware |
| [machine\_code](Progs/machine_code/) | Machine code interface demos — Z80 routines called from Hunter BASIC via `ARG`/`CALL`; BDOS console output and Collatz BASIC-vs-MC benchmark | Working on hardware |
| [PONGGAME](Progs/pong/) | Single-player Pong — paddle, collision, beep on miss, configurable speed. 451 bytes of Z80 MC. Is this the first game for the Husky Hunter! | Working on hardware |
| [defendERR](Progs/defenderr/) | Early preview of a Defender-style side-scroller (ship, stars, fire, enemies, collision, and movement variants) | Early preview |
| [Animation](Progs/Animation/) | MC-driven sprite animations — horizontal, wave-motion, two-sprite, and Pong-style bouncing ball, all running in Z80 machine code with BASIC loader | Working on hardware |
| [Y2K](Y2K/) | Y2K date fix — patches the ROM's hardcoded `19xx` century to `20xx` via a 12-byte COM utility or BASIC one-liner | Working on hardware |

## PC Tools

Tools that run on the PC to support the Hunter programs above.

| Tool | Description | Status |
| ---- | ----------- | ------ |
| [HBA\_Format](HBA_Format/README.md) | Tokenizer (`HBA_Tokenizer.exe`, `hba_tokenize.py`) — converts `.BAS` source to `.HBA` binary; includes file format reference and token table | Working |
| [HuskyHCOM](HuskyHCOM/) | HCOM file transfer launcher for modern 64-bit Windows — DOSBox-based with interactive setup, auto COM port detection, and dev sync workflow | Working |

## Reference

* [HUNTER\_BASIC\_GOTCHAS.md](HUNTER_BASIC_GOTCHAS.md) — Hunter BASIC syntax differences, reserved words, and quirks discovered during hardware testing
* [RS232\_REFERENCE.md](RS232_REFERENCE.md) — RS-232 serial port configuration via POKE — baud rates, parity, handshaking, and BASIC I/O commands
* [HBA\_Format/](HBA_Format/README.md) — Tokenizer tools (`HBA_Tokenizer.exe`, `hba_tokenize.py`), file format reference, and token table
* [HBA\_Format/TOKEN\_REFERENCE.md](HBA_Format/TOKEN_REFERENCE.md) — Reverse-engineered Hunter BASIC token byte assignments

## The Husky Hunter

Ruggedised portable field computer by DVW Microelectronics / Husky Computers Ltd, Coventry (1983).

| Spec | Detail |
| ---- | ------ |
| CPU | NSC800-4 @ 4 MHz (CMOS Z80-compatible) |
| RAM | 80K / 144K / 208K, battery-backed CMOS |
| ROM | 48K firmware in EPROMs |
| Display | 240 × 64 dot LCD |
| Serial | RS-232 up to 4800 baud |
| OS | DEMOS 2.2 (CP/M 2.2 derivative, RAM-disk) |

Micro Live S02E02: https://www.youtube.com/watch?v=y1ZBr3NInow&t=739s

## Acknowledgements

* [TheEPROM9 — Husky Hunter/Hunter 2](https://www.theeprom9.co.uk/vintage-computers/husky-computer-archive/husky-hunterhunter-2) — hardware teardowns, ROM dumps, reverse engineering efforts, demo code listings, and LCD datasheet

## GitHub Community

* [Kayto/Husky-Hunter](https://github.com/Kayto/Husky-Hunter) — Hunter BASIC programs, HBA tokenizer, HCOM launcher, and RS-232 tools for the 1983 Husky Hunter

Other Husky-related projects and resources on GitHub:


* [NicolaCowie/HCOM](https://github.com/NicolaCowie/HCOM) — original HCOM PC-to-Husky file transfer software (v1.0). Source code in C and Assembly for Hunter 1 & 2, Hawk, Hunter 16 and FS2
* [sleepygecko/husky](https://github.com/sleepygecko/husky) — Husky Computers related information, HCOM WIN11 binaries, and Hunter 16 manual chapters
* [TheEPROM9/Husky-Computer-Software](https://github.com/TheEPROM9/Husky-Computer-Software) — collected software for Husky computers. CP/M, DEMOS, HCOM, and MS-DOS utilities from the DVW Microelectronics Husky through to MS-DOS models
* [TheEPROM9/Husky-Computer-ROM-Images](https://github.com/TheEPROM9/Husky-Computer-ROM-Images) — archive of ROM images pulled from Husky computers: Hunter, Hunter 16, Hunter 16-80, Hawk, FS2, FS3, and more

## License

MIT License. See [LICENSE](LICENSE) for details.
