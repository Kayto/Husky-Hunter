# Husky Hunter — ROM Symbol Reference

An address-sorted index of every routine, data table and RAM variable identified and named so far by disassembly analysis of the 1983 Husky Hunter firmware.

*Work in progress — not final.*

## About this firmware

The **Husky Hunter** was a rugged, battery-powered handheld computer launched
in **1983** by **DVW Microelectronics** (later Husky Computers Ltd) of
Coventry, UK. This reference indexes its original 6 × 8 KB EPROM firmware
running **DEMOS 2.2** (build `9G06h`) — *Disk EMulation Operating System
version 2.2*, Husky's CP/M-compatible OS for handheld use. The machine ran an
**NSC800** CPU (4 MHz, Z80-compatible CMOS), a **240 × 64 pixel LCD**, a
**sealed chiclet QWERTY keyboard**, an **MM58174A** real-time clock and
an **RS-232 / V24** serial port — all in a waterproof diecast-aluminium case.
Battery-backed CMOS RAM kept user programs and the clock alive between power
cycles.

## The 1983 ROM set (6 × 8 KB EPROMs, 48 KB total)

The firmware lives in six **2764-type EPROMs** concatenated into one flat
48 KB image at `0000H–BFFFH`. Each EPROM holds a different layer of the
system:

| EPROM | Address range  | Contents |
|------:|----------------|----------|
|     0 | `0000H–1FFFH`  | Boot vectors, the main interrupt handlers, the BIOS dispatcher and the keyboard / serial input stubs |
|     1 | `2000H–3FFFH`  | The BASIC interpreter — keyword tables, token tables, expression evaluator, floating-point maths |
|     2 | `4000H–5FFFH`  | BASIC runtime + the comms menu UI — serial parameter setup, baud-rate dialog, application menu |
|     3 | `6000H–7FFFH`  | The comms protocol engine — V24 / RS-232, XON/XOFF, IBM bisync + EBCDIC translation table |
|     4 | `8000H–9FFFH`  | The text editor and clock / calendar code — edit-mode UI, soft-key labels, time-setting |
|     5 | `A000H–BFFFH`  | The OS kernel, file system, DEMOS command shell, error messages, LCD font glyphs |

Each EPROM is byte-identical to dumps captured from a working 1983 device —
sourced from
[TheEPROM9/Husky-Computer-ROM-Images](https://github.com/TheEPROM9/Husky-Computer-ROM-Images),
an archive of ROM images pulled from Husky computers (Hunter, Hunter 16,
Hunter 16-80, Hawk, FS2, FS3 and more).  For verification, the SHA1 hashes
of the six 8 KB images are:

| EPROM | SHA1 |
|------:|------|
|     0 | `fe8bcad60d4a0dc94cc6756d9132743f27fbb65d` |
|     1 | `4235b4483ea8a091d332248074f72f220692c05e` |
|     2 | `02a0ce58405e95b48f7ac8aa291cb836a6927375` |
|     3 | `73fc7f953b56d491ad4fcfe80636db0150a718dc` |
|     4 | `6667fbd5583217ea7ba9b4b4fc9dc56240b0e14e` |
|     5 | `bd8f5a37e5f16511623dc128e2b95b4866b4297a` |

## Memory map at a glance

| Range          | What lives there |
|----------------|------------------|
| `0000H–BFFFH`  | **ROM** — the 6 EPROMs above (paged out only when the OS swaps in a RAM bank via `OUT (E0H),A` with bit 7 set) |
| `C000H–FFFFH`  | **RAM** — battery-backed CMOS holding system variables, the virtual screen, the serial buffers and the OS stacks |
| `E000H–EFFFH`  | A **RAM mirror of EPROM 0's first 4 KB** — kept live in RAM so interrupt vectors and the RST 18 / RST 20 dispatchers stay reachable when ROM is paged out |

This is why the symbol table below has just two regions — `ROM` for everything
the firmware ships in EPROM, `RAM` for everything the firmware writes (or
mirrors) at run time.

---

## Symbol table

| Addr | Name | Region | Summary |
|------|------|:------:|---------|
| `0000H` | `RESET` | ROM | CPU reset — cold-boot entry point |
| `0005H` | `BDOS` | ROM | CP/M-style BDOS call entry |
| `0008H` | `RST_08` | ROM | Restart vector 08 (unused) |
| `0010H` | `RST_10` | ROM | Restart vector 10 (unused in this firmware) |
| `0018H` | `RST_18` | ROM | Restart vector 18 — main BIOS call dispatcher |
| `0020H` | `RST_20` | ROM | Restart vector 20 — paged-RAM call dispatcher |
| `0028H` | `RST_28` | ROM | Restart vector 28 — keyboard / display service |
| `0030H` | `RST_30` | ROM | Restart vector 30 (unused) |
| `0038H` | `INT_IM1` | ROM | Maskable-interrupt entry (IM 1 mode) |
| `0066H` | `NMI` | ROM | Non-maskable interrupt — 61 Hz keyboard / sound tick |
| `0069H` | `CHAR_CLASSIFY` | ROM | Classify the next input character (CR → tokenise, '=' → buffer advance, else store) |
| `007CH` | `SERIAL_DSR_CHK` | ROM | Abort guard: returns if DSR (modem ready) is low |
| `0081H` | `SERIAL_FETCH_CHAR` | ROM | Fetch next char from the serial buffer into the TX state machine |
| `0088H` | `SERIAL_INT_CTX` | ROM | Save/restore interrupt-mask register around the serial ISR |
| `00A3H` | `SERIAL_LOCK_CHK` | ROM | Guard: return if the serial mode-lock flag is set |
| `00A8H` | `SERIAL_TX_DONE` | ROM | Serial transmit complete — final state in the TX state machine |
| `00AEH` | `SERIAL_TX_START` | ROM | Send the serial start bit (the first low bit of a byte) |
| `00B5H` | `SERIAL_TX_BIT_HI` | ROM | Send a serial '1' (high) bit |
| `00C0H` | `SERIAL_TX_BIT_LO` | ROM | Send a serial '0' (low) bit |
| `00CBH` | `SERIAL_TX_STOP` | ROM | Send the serial stop bit and shut down the bit-clock timer |
| `00E0H` | `SERIAL_BUF_EMPTY` | ROM | Mark serial buffer empty and jump to advance the read pointer |
| `00E5H` | `SERIAL_BUF_ADV` | ROM | Advance to the next byte in the serial transmit buffer |
| `0100H` | `BOOT_SET_SP` | ROM | Boot: initialise the stack pointer |
| `0101H` | `SERIAL_STORE_DISP` | ROM | Forward a serial character into the display path |
| `0106H` | `SERIAL_BUF_END` | ROM | Serial buffer exhausted — arm the stop-bit transition |
| `0112H` | `SERIAL_M12_FETCH` | ROM | Alt fetch path for mode-12 serial output |
| `0120H` | `COLD_START` | ROM | Cold start: clear RAM and jump into the OS init |
| `0135H` | `WARM_START_CHK` | ROM | Decide whether this boot is warm or cold |
| `015FH` | `EPROM0_TOKEN_TBL` | ROM | BASIC keyword suffix lookup table (data) |
| `0180H` | `NMI_TICK_ISR` | ROM | NMI handler: 61 Hz tick — start of the NMI stub bank |
| `0188H` | `NMI_STUB_B` | ROM | NMI handler: delay-count loop into paged RAM |
| `0196H` | `NMI_STUB_C` | ROM | NMI handler: snapshot Port B/C inputs and arm the interrupt mask |
| `01C6H` | `NMI_STUB_D` | ROM | NMI handler: Timer-B high-byte read path |
| `01DBH` | `NMI_STUB_E` | ROM | NMI handler: re-arm Timer B to max count |
| `01ECH` | `NMI_MAIN_TICK` | ROM | NMI handler: main 61 Hz body (stack guard + service calls) |
| `023BH` | `NMI_KBD_BUF` | ROM | NMI handler: store a keyboard character into the input slot |
| `0241H` | `NMI_TIMER_PROG` | ROM | NMI handler: reprogram Timer B from the saved count pair |
| `0257H` | `NMI_TIMER_READ` | ROM | NMI handler: read the high byte of Timer B and re-enable interrupts |
| `025EH` | `NMI_PORTC_CTR` | ROM | NMI handler: Port C bit-2 edge counter / dispatch |
| `028EH` | `NMI_KBD_SCAN` | ROM | NMI handler: full keyboard matrix scan |
| `02BDH` | `NMI_FRAG_F992` | ROM | NMI handler: tiny dispatch fragment |
| `02C3H` | `RST18_ADDR_TBL` | ROM | Address table for RST 18 BIOS-call targets |
| `02F3H` | `RST20_ADDR_TBL` | ROM | Address table for RST 20 paged-RAM-call targets |
| `04DDH` | `PAGED_COLD_INIT` | ROM | Cold init for the paged-RAM window |
| `065BH` | `SOUND_ISR_AREA` | ROM | Sound ISR area start (disasm_1983.py) |
| `067DH` | `SOUND_ISR` | ROM | SOUND interrupt handler |
| `0DF9H` | `KWD_SCAN_E0` | ROM | BASIC keyword scan, token base E0 |
| `0F2CH` | `SCROLL_BUF_SYNC` | ROM | Sync the scroll buffer (used by BASIC restart and tape scroll) |
| `0F56H` | `PROG_END_HDL` | ROM | BASIC program end |
| `0FF4H` | `BASIC_NEXT` | ROM | Interpreter NEXT loop entry |
| `0FFDH` | `STMT_EXEC` | ROM | BASIC statement executor — the most-called interpreter routine |
| `106EH` | `TOKEN_DISPATCH` | ROM | Token/operator handler dispatcher: read dispatch byte from (HL) |
| `1108H` | `PRINT_PROG_STATUS` | ROM | Print interpreter status message |
| `115CH` | `GFX_MODE_INIT` | ROM | Set cursor state + GFX mode |
| `121CH` | `LIST_PRINT_LINE` | ROM | Print one detokenised BASIC line |
| `1245H` | `LIST_SCAN_LOOP` | ROM | LIST main scan loop: check token 1BH/1FH (skip) |
| `1417H` | `BASIC_PEEK` | ROM | Peek the current BASIC token without advancing |
| `1473H` | `KWD_DISPATCH` | ROM | Dispatch a BASIC keyword via its jump table |
| `147DH` | `EXPR_INIT` | ROM | Initialise the expression output buffer pointer |
| `1648H` | `IS_VALUE_TOKEN` | ROM | Return Z=1 if the current BASIC token is a value (string/number) |
| `16F7H` | `EVAL_SUBEXPR_NORM` | ROM | EVAL_SUBEXPR then — eval a sub-expression + normalise |
| `16FDH` | `EVAL_SUBEXPR` | ROM | Evaluate an expression with the evaluator context saved/restored |
| `1722H` | `SCAN_RPAREN` | ROM | Scan for a closing ')' |
| `1724H` | `SCAN_KWD_CHK` | ROM | Scan for a keyword (helper) |
| `1727H` | `SCAN_COMMA` | ROM | Scan for a ',' |
| `1813H` | `EXPR_DISPATCH` | ROM | Expression evaluator token dispatcher |
| `1A5CH` | `EVAL_TWO_ARGS` | ROM | Evaluate two comma-separated floating-point arguments |
| `1BD8H` | `PRINT_SEP_HDL` | ROM | PRINT separator handler |
| `1C4CH` | `PRINT_SPACE` | ROM | Output a single space character |
| `1DB1H` | `PEEK_NEXT_TOK_CP90` | ROM | Peek the *next* token (alt HL+1, no advance) and CP 90H — lookahead test |
| `1E7FH` | `EVAL_NORM_ARG` | ROM | Evaluate an expression and normalise the result |
| `1E9DH` | `CHK_COMMA_FETCH` | ROM | Require a comma in the BASIC source |
| `1EA4H` | `TOKEN_FETCH` | ROM | Fetch the next BASIC token byte (advances the interpreter) |
| `1EA9H` | `PROG_FETCH` | ROM | Advance and fetch the next BASIC program byte |
| `1EAEH` | `PEEK_TOK_CP30` | ROM | Peek the current token (alt HL) and CP 30H ('0') — token classify |
| `1EB6H` | `CHK_COMMA` | ROM | Check for a comma in argument-list parsing |
| `1EBCH` | `EVAL_EXPR` | ROM | Main BASIC expression evaluator entry point |
| `205BH` | `TOKENIZE_LINE` | ROM | Encode an ASCII BASIC line into stored token form |
| `2156H` | `EPROM1_TOKEN_TBL` | ROM | BASIC token text table (data) |
| `2367H` | `TOKEN_TBL_MID` | ROM | Midpoint of the BASIC token table |
| `246DH` | `DETOKENIZE_LINE` | ROM | Expand stored tokens back to ASCII (used by LIST) |
| `265FH` | `KWD_HANDLER_TBL` | ROM | BASIC keyword handler jump table (data) |
| `272FH` | `OP_DISPATCH_TBL` | ROM | BASIC operator dispatch + precedence table (data) |
| `2813H` | `PRINT_ERR_BANNER` | ROM | Print error banner |
| `283BH` | `SCAN_TO_CR` | ROM | Called from 2C8EH (token FEH+8FH path) |
| `2856H` | `COMPARE_LT` | ROM | BASIC '<' comparison operator |
| `2869H` | `COMPARE_GT` | ROM | BASIC '>' comparison operator |
| `2886H` | `COMPARE_EQ` | ROM | BASIC '=' comparison operator |
| `288DH` | `COMPARE_NE` | ROM | BASIC '<>' (not equal) comparison operator |
| `2894H` | `COMPARE_LE` | ROM | BASIC '<=' comparison operator |
| `289DH` | `COMPARE_GE` | ROM | BASIC '>=' comparison operator |
| `28A6H` | `STR_COMPARE` | ROM | Compare two byte sequences (used by string equality and ordering) |
| `28F1H` | `FLOAT_ADD_OP` | ROM | Floating-point add operator |
| `28F5H` | `FLOAT_ADD_INNER` | ROM | Inner body of the floating-point add operator (after register swap) |
| `28FAH` | `FLOAT_SUB_OP` | ROM | Floating-point subtract operator |
| `28FEH` | `FLOAT_SUB_INNER` | ROM | Inner body of the floating-point subtract operator (after register swap) |
| `290BH` | `FLOAT_MUL_OP` | ROM | Floating-point multiply operator |
| `290FH` | `FLOAT_MUL_INNER` | ROM | Inner body of the floating-point multiply operator (after register swap) |
| `2914H` | `FLOAT_DIV_OP` | ROM | Floating-point divide operator |
| `2918H` | `FLOAT_DIV_INNER` | ROM | Inner body of the floating-point divide operator (after register swap) |
| `291BH` | `ARITH_EXIT` | ROM | Arithmetic shared exit: load RAM |
| `2941H` | `BOOL_FLIP` | ROM | Boolean NOT — flips true/false on a result byte |
| `296EH` | `FP_MUL_POLY` | ROM | Floating-point multiply polynomial step |
| `29AFH` | `FP_ADD_POLY` | ROM | Floating-point add polynomial step |
| `2A04H` | `FP_RATIONAL_EVAL` | ROM | Floating-point rational function evaluation |
| `2A7DH` | `FP_MADD_STEP` | ROM | Floating-point multiply-add step |
| `2A9BH` | `GET_HEAP` | ROM | Load current float heap ptr |
| `2AA2H` | `FP_POLY_EVAL` | ROM | Floating-point polynomial evaluator core: pop exponent byte from heap |
| `2BC7H` | `FLOAT_NORMALISE` | ROM | BCD float normalise: if exponent < 81H zero all 9 bytes (underflow→0) |
| `2BE8H` | `PARSE_EXPR` | ROM | Expression parse entry |
| `2C7DH` | `SKIP_STMT_SEP` | ROM | Skip statement separator: TOKEN_FETCH |
| `2CADH` | `SCAN_IDENT` | ROM | Scan identifier/variable name: uppercase (RES 5), collect up to 10 |
| `2CC7H` | `GET_ALPHA_CHK` | ROM | Fetch current EXX-HL char and test if alphabetic A-Za-z |
| `2CCCH` | `SCAN_ALNUM` | ROM | Scan single alphanumeric char from EXX-HL: alpha (A-Za-z) or digit (0-9) |
| `2CE1H` | `SCAN_DIGIT` | ROM | Scan single decimal digit (0-9) from EXX-HL |
| `2D0CH` | `HEAP_ALLOC` | ROM | Advance RAM float heap ptr by +9 (allocate one 9-byte float slot) |
| `2D19H` | `FLOAT_COPY` | ROM | Copy 9 bytes from (HL) to — reverse decrement direction |
| `2D54H` | `KWD_SCAN_ENTRY` | ROM | Keyword scan entry point |
| `2D5DH` | `PRINT_TO_CR` | ROM | Print string from HL until CR |
| `2D61H` | `PRINT_QUOTED_STR` | ROM | Print string from HL until '"' or CR |
| `2DB4H` | `CHECK_PROG_MODE` | ROM | Check RAM program-run flag |
| `2DBFH` | `NORMALISE_ARG` | ROM | Normalise top-of-heap float |
| `2DFCH` | `BCD_MUL10_ACC` | ROM | Multiply DE by 10 and add digit nibble from A: HL=DE×10 (via ×2×2+1×2) |
| `2E16H` | `PARSE_DEC_INT` | ROM | Parse decimal integer from EXX-HL input stream into DE |
| `2E2EH` | `INT_TO_DEC` | ROM | Convert 16-bit integer HL to decimal ASCII |
| `2E53H` | `DEC_DIGIT_LOOP` | ROM | Inner decimal digit loop: repeatedly ADD BC (negative power-of-10) to HL |
| `2E6DH` | `GET_CHAR_ECHO` | ROM | Read one keyboard character and echo it to the display |
| `2EB0H` | `BASIC_RESET` | ROM | Clear output/display state |
| `2EE9H` | `WAIT_KEY_CHAR` | ROM | Wait for a keyboard character |
| `2F08H` | `PUTCHAR` | ROM | Primary character output dispatcher (most-called routine in ROM) |
| `2F39H` | `PUTCHAR_CRLF` | ROM | Emit CR through the output gate |
| `2F3CH` | `PUTCHAR_GATE` | ROM | Output gate — suppresses output when the gate flag is set |
| `2F54H` | `PUTCHAR_CR` | ROM | Output a CR (carriage return) character |
| `316EH` | `CHAR_OUT_BUF` | ROM | Check 0F7CEH: if 0 → (direct) |
| `32E6H` | `FLOAT_SUB` | ROM | Float subtract primitive: negate mantissa then add |
| `32F3H` | `FLOAT_ADD` | ROM | Float add primitive: align exponents + BCD-add mantissas |
| `340AH` | `FLOAT_MUL` | ROM | Float multiply primitive |
| `3517H` | `FLOAT_DIV` | ROM | Float divide primitive |
| `362BH` | `DISP_MODE_MSG` | ROM | Select an EPROM5 message string by |
| `3C93H` | `FP_COPY_NORM` | ROM | Floating-point copy + normalise |
| `3E11H` | `FP_SERIES_EVAL` | ROM | Floating-point transcendental series evaluator: uses FLOAT_MUL/ADD/SUB/DIV_INNER |
| `3E6FH` | `FP_MUL_DIV_STEP` | ROM | Floating-point multiply+divide step |
| `3F21H` | `FP_COPY_SUB` | ROM | Floating-point copy + subtract |
| `3F4FH` | `FP_HEAP_TO_BC` | ROM | LD HL,(RAM_FP_HEAP) |
| `3FBAH` | `FP_MUL_ACCUM` | ROM | Floating-point multiply accumulate |
| `40E0H` | `POW_OP` | ROM | Power operator (token E1H = `**` or `^`, prec=12) |
| `4256H` | `PRINT_TWO_EXPR` | ROM | PRINT two comma-separated expressions |
| `42AEH` | `STMT_KWD_EXPR` | ROM | Keyword expression statement handler |
| `4439H` | `ALT_CHAR_OUT` | ROM | Alternate/windowed text output (PUTCHAR middle path: RAM≠0, bit7=0) |
| `4502H` | `EVAL_COMMA_CHK` | ROM | Evaluate expression + comma check |
| `4581H` | `FILE_STMT_PARSE` | ROM | File statement parser |
| `4647H` | `WIN_CHAR_ROUTE` | ROM | Window/terminal output router: char → paged RAM window system |
| `465BH` | `TEST_STMT_SEP` | ROM | Returns Z set if current char is CR or ':' |
| `4661H` | `CHK_STMT_END` | ROM | Check for end of BASIC statement |
| `4678H` | `EVAL_NORM_EXPR` | ROM | Evaluate an expression and normalise the result |
| `468CH` | `BITWISE_AND_OP` | ROM | Integer AND operator (token EDH) |
| `46F0H` | `BITWISE_OR_OP` | ROM | Integer OR operator (token EEH) |
| `46FFH` | `BITWISE_XOR_OP` | ROM | Integer XOR operator (token EFH) |
| `4709H` | `NOT_OP` | ROM | NOT operator (token F3H, prec=13) |
| `4793H` | `EQV_OP` | ROM | EQV operator (token F0H, prec=2) |
| `479DH` | `IMP_OP` | ROM | IMP operator (token F2H, prec=2) |
| `482AH` | `MACHINE_TYPE_DETECT` | ROM | Machine type detection |
| `4859H` | `WARM_INIT` | ROM | Main application init: clear RAM, reset SP=RAM, init RAM flags |
| `48B6H` | `DISP_KBD_INIT` | ROM | Display + keyboard init sequence |
| `4940H` | `LOAD_COMPLETE_RST` | ROM | Post-load completion: redraw menu + scan keyboard |
| `4953H` | `TIMER_B_INIT` | ROM | Initialise NSC810 Timer B (used by the keyboard / sound tick) |
| `4969H` | `BASIC_STARTUP` | ROM | BASIC start-up routine (called after warm-init) |
| `49D7H` | `MENU_DISPATCH` | ROM | Dispatch a menu selection |
| `4A39H` | `CURSOR_SET_POS` | ROM | Set the cursor position from HL |
| `4A48H` | `MENU_ITEM_DISP` | ROM | Display the menu items |
| `4A56H` | `REENTR_GUARD` | ROM | Re-entrancy guard on RAM: if nonzero → POP+return A=0 (skip) |
| `4A64H` | `COMMS_MODE_CHK` | ROM | Check the comms-mode flag; if set, initialise the serial port |
| `4A8DH` | `CURSOR_MOVE_MAIN` | ROM | Cursor movement main entry |
| `4A9EH` | `CURSOR_EXIT` | ROM | Clear the cursor re-entrancy flag |
| `4AA3H` | `LCD_ADDR_SAVE` | ROM | Save / restore the LCD cursor address |
| `4AB3H` | `CURSOR_WIN_SETUP` | ROM | Set up a display window |
| `4AEFH` | `CURSOR_SCROLL_DN` | ROM | Scroll down (advance cursor row) |
| `4B06H` | `CURSOR_SCROLL_UP` | ROM | Scroll up (falls into scroll-down if disabled) |
| `4B19H` | `CURSOR_COL_DEC` | ROM | Cursor column decrement: guard → check RAM |
| `4B2BH` | `CURSOR_HOME` | ROM | Move cursor home (page up) |
| `4B40H` | `CURSOR_END` | ROM | Move cursor to end (page down) |
| `4B54H` | `CURSOR_INBOUND` | ROM | Check the cursor is within window bounds |
| `4B72H` | `CURSOR_OFFSET_CALC` | ROM | Compute the screen offset for the cursor |
| `4B94H` | `STR_TABLE_BUILD` | ROM | Copy null/CR-terminated string from HL into RAM table |
| `4BB6H` | `CURSOR_BLINK_TOG` | ROM | Toggle cursor blink |
| `4C0BH` | `LCD_CLEAR_ROW` | ROM | Clear LCD row at current position: send cursor addr |
| `4C4AH` | `SET_CONTRAST` | ROM | Set LCD contrast / brightness |
| `4C53H` | `DELAY_2560` | ROM | Short countdown delay (~2560 cycles) |
| `4C5EH` | `KBD_SCAN_ALL` | ROM | All-rows keyboard scan |
| `4C97H` | `KBD_MATRIX_SCAN` | ROM | Full 7-column keyboard matrix scan |
| `4CBCH` | `KBD_RELEASE` | ROM | Release keyboard scan lines |
| `4CDBH` | `KBD_POLL_MAIN` | ROM | Main keyboard polling loop |
| `4CF2H` | `KBD_COMMS_CHK` | ROM | Serial/comms keyboard input check: read IN bit0 |
| `4D33H` | `KBD_DEBOUNCE_SCAN` | ROM | Keyboard debounce scan |
| `4D45H` | `KBD_SCAN_STORE` | ROM | Store scan result |
| `4D63H` | `KBD_REPEAT_MGR` | ROM | Key repeat manager |
| `4DA8H` | `KBD_COL_SCAN` | ROM | Read one column of the keyboard matrix |
| `4DC2H` | `KBD_STATE_MERGE` | ROM | Update the key-state byte after a scan |
| `4DCBH` | `KBD_FULL_SCAN` | ROM | Full keyboard matrix scan with state update |
| `4DF6H` | `SERIAL_INPUT_START` | ROM | Serial character input — start of input cycle |
| `4E11H` | `KBD_NO_KEY_CHK` | ROM | No-key check |
| `4E2FH` | `KBD_KEY_DECODE` | ROM | Decode the pressed key from the scan result |
| `4E76H` | `KBD_CHAR_PROC` | ROM | Process a decoded keyboard character |
| `5040H` | `KBD_PORT_DETECT` | ROM | Detect the keyboard port (skip init if already done) |
| `50E5H` | `KBD_KEY_FIND` | ROM | Find a key code in the 112-entry key-character table |
| `51DEH` | `SERIAL_CHAR_TICK` | ROM | Serial/terminal char input state machine (called from NMI_MAIN_TICK) |
| `539EH` | `KBD_POLL` | ROM | Keyboard polling helper (calls into the paged-RAM GETKEY) |
| `53A8H` | `LINE_EDITOR` | ROM | Full line input + callback dispatch |
| `53B6H` | `SERIAL_VEC_DISPATCH` | ROM | Serial input vector dispatch (gated on the comms-mode flag) |
| `5492H` | `GFXCHAR_WAIT` | ROM | Output a graphics character and wait for the LCD |
| `54A8H` | `GFX_CHAR_OUT` | ROM | Bitmap char renderer (PUTCHAR gfx path: RAM bit7=1) |
| `564EH` | `PIXEL_COL_WRITE` | ROM | LCD controller pixel column writer |
| `565AH` | `LCD_COL_PIXEL` | ROM | Inner column write |
| `568AH` | `DISP_SERIAL_INIT` | ROM | Display + serial mode init |
| `598BH` | `FMT_2DIGIT_ASCII` | ROM | Format two RTC bytes as ASCII (digits 0-9) |
| `5A8BH` | `MENU_SERIAL_INIT` | ROM | Menu + serial mode init |
| `5C3DH` | `STR_SCAN_CHAR` | ROM | Scan one character of a quoted string |
| `5FDFH` | `SERIAL_BAUD_LOOKUP` | ROM | Set HL=SERIAL_BAUD_TABLE, BC=0002H, fall through to 62CFH |
| `5FE2H` | `SERIAL_TABLE_WALK` | ROM | Entry with BC pre-loaded (stride) |
| `5FE5H` | `SERIAL_TABLE_FETCH` | ROM | Entry with HL and BC pre-loaded |
| `6081H` | `SOUND_MODE_INIT` | ROM | SOUND-mode init: arm Timer-0 NMI for the audio bit-banger |
| `6136H` | `TAPE_SYS_INIT` | ROM | Tape + system init: LCD_GATE_ALL_SET |
| `626BH` | `LCD_GATE_ALL_SET` | ROM | Enables all three LCD column-gate flags in one call |
| `6277H` | `NMI_HOOK_INSTALL` | ROM | Install one of the NMI hook templates into the NMI shadow |
| `6288H` | `NMI_HOOK_TMPL_A` | ROM | Non-maskable interrupt hook template A (40 bytes, LDIR'd to F814H) |
| `62AEH` | `NMI_HOOK_TMPL_B` | ROM | Non-maskable interrupt hook template B (alt) |
| `62CFH` | `BAUD_TBL_WALK` | ROM | Shared walker used by the baud-table lookup helpers |
| `62DBH` | `TABLE_IDX_GET` | ROM | Walk a 2-byte-per-entry table by index (capped to 6 entries) |
| `62EAH` | `SERIAL_BAUD_TABLE` | ROM | Per-baud Timer-0 reload count table (11 entries, 75 → 9600 baud) |
| `6300H` | `SERIAL_BAUD_TBL2` | ROM | Mirror of SERIAL_BAUD_TABLE used by the alt channel |
| `63ABH` | `TAPE_MODE_CHK` | ROM | Return Z=1 if tape or terminal mode is active |
| `63B7H` | `BAUD10_CHK` | ROM | Return Z=1 if the device is configured for baud setting 10 (9600) |
| `63C8H` | `SOUND_NMI_TICK` | ROM | Non-maskable interrupt sound tick: feeds phase counter F864H to tone handler 770EH |
| `63E9H` | `NMI_ALTW_ENTRY` | ROM | Alt-warm non-maskable interrupt entry |
| `6500H` | `LCD_COL_QUEUE` | ROM | Queue LCD column write |
| `6523H` | `LCD_COL_STORE` | ROM | Store col A to (RAM) |
| `65AFH` | `DISP_FULL_INIT` | ROM | Full display + kbd + serial init: check 0F85AH |
| `6612H` | `CHAR_SEND_INIT` | ROM | Send a character and reset the display state slots |
| `6767H` | `CHAR_LCD_RESET` | ROM | Char output + LCD gate + KB reset |
| `67F7H` | `KB_STATE_RESET` | ROM | Resets keyboard character-input FSM to idle state |
| `6BC8H` | `CHAR_PAGED_CALL` | ROM | Paged character output with interrupt lock |
| `6BDBH` | `SET_LCD_GATE_C3` | ROM | Enable the LCD column-gate 'C3' (from the gfx output path) |
| `6BE1H` | `SET_LCD_GATE_94` | ROM | Enable the LCD column-gate '94' (companion to gate C3) |
| `6BE7H` | `SERIAL_TX_PREP` | ROM | Serial transmit prep / RTS handshake |
| `6D00H` | `EBCDIC_TO_ASCII` | ROM | EBCDIC → ASCII translation table for bisync comms (data) |
| `6E0DH` | `HEX_DUMP_LOOP` | ROM | Loop that hex-dumps a region of memory to the display |
| `6E41H` | `EPROM3_STR_PRINT` | ROM | Print a $-terminated EPROM3 message string from HL |
| `6E51H` | `SEND_CRLF` | ROM | Send CRLF (carriage-return + line-feed) |
| `6E5BH` | `ASCII_HEX_TO_NIB` | ROM | ASCII hex char ('0'-'9','A'-'F') -> nibble 0-FH in A |
| `6E6FH` | `PTR_RANGE_CHK` | ROM | Pointer range check (compare HL against bounds) |
| `6E7EH` | `HEX_BYTE_DISP` | ROM | Display byte A as 2 hex ASCII chars: high nibble via TAPE_SCROLL_COL |
| `6EA1H` | `NIBBLE_TO_HEX` | ROM | Convert a 4-bit nibble to its hex ASCII character |
| `6EABH` | `TAPE_READ_CHAR` | ROM | Read one char from tape (+ baud context save) |
| `6ED7H` | `DISP_CHAR_GFX` | ROM | Display A on LCD |
| `6EDEH` | `TAPE_READ_HEX` | ROM | Read 2 ASCII hex nibbles from tape -> packed byte in A (C=A) |
| `6F03H` | `INTEL_HEX_LOAD` | ROM | Intel HEX tape loader: wait ':', read addr (3 bytes), read data block |
| `6F77H` | `PAGED_JUMP_TBL` | ROM | Paged-RAM jump table |
| `6FD5H` | `TAPE_TIMER` | ROM | Tape baud-rate timer / counter |
| `6FE8H` | `PORT42_SAMPLE` | ROM | Read the RTC time register at port 42H |
| `6FF8H` | `TAPE_BAUD_SAVE` | ROM | Save the computed tape baud parameter |
| `7008H` | `TAPE_BAUD_SAVE_B` | ROM | Save the computed tape baud parameter (alt slot) |
| `7016H` | `BAUD_SCALE` | ROM | Scale a BCD value × 10 for tape baud computation |
| `7034H` | `CLOCK_TICK_SCALE` | ROM | Port 42H+43H time sampling ×10: used by BAUD_SCALE + clock code |
| `7044H` | `TAPE_RESTART` | ROM | Restart the tape state machine |
| `7068H` | `CLR_TAPE_FLAG` | ROM | Clear the tape / serial activity flag |
| `7073H` | `PRINT_STR` | ROM | Print $-terminated string from HL |
| `7086H` | `GET_CURSOR` | ROM | Get the current cursor position |
| `708AH` | `SET_CURSOR` | ROM | Set the cursor position |
| `708EH` | `MENU_COL_SAVE` | ROM | Save the current menu column |
| `70A0H` | `LCD_WRITE` | ROM | Write a byte to the LCD controller (with busy-poll) |
| `70ADH` | `LCD_WAIT` | ROM | LCD controller busy-wait loop |
| `70BAH` | `DISP_CLS` | ROM | Clear the display (DISPCLS) |
| `70EEH` | `MENU_REDRAW` | ROM | (menu re-entry, guarded by RAM_MENU_REENTR) |
| `70FFH` | `TEST_PRINT_FLAG` | ROM | Test the BASIC print-active gate flag |
| `717DH` | `CHAR_OUT_WRAP` | ROM | CHAR_OUT with wrap/paging |
| `71D5H` | `CHAR_OUT` | ROM | Character output dispatcher |
| `7378H` | `DISP_STATE_LOAD` | ROM | Reload the display state from RAM |
| `7385H` | `LCD_WRITE_AT` | ROM | Write data byte A at cursor position (RAM-1) |
| `7392H` | `LCD_WRITE_ADDR` | ROM | Set the LCD cursor address |
| `7395H` | `LCD_SEND_ADDR` | ROM | Send HL as 2-byte cursor address |
| `73A0H` | `COL_BOUNDARY_CHK` | ROM | Test HL vs 40-col multiples (0x28/0x50/0x78/0xA0/0xC8/0xF0/0x18/0x40) |
| `73C5H` | `GETCHAR_ECHO` | ROM | Get char from serial/kbd |
| `73DAH` | `LCD_COL_WRITE` | ROM | Low-level LCD pixel column write |
| `748AH` | `TAPE_SCROLL_COL` | ROM | Scroll one LCD column using circular ticker-tape buffer at DFB0H/DFB2H |
| `74ACH` | `SCROLL_COL_WRITE` | ROM | Write A to circular scroll ticker-tape buffer |
| `74E5H` | `CHAR_INPUT_DISP` | ROM | Char input dispatcher (keyboard / serial routing) |
| `7503H` | `KBD_CURSOR_DISP` | ROM | Display the keyboard-driven cursor |
| `770EH` | `SOUND_STOP_CHK` | ROM | Pops return addr when sound finishes |
| `779CH` | `DISP_KBD_CYCLE` | ROM | Display+kbd combined scan wrapper |
| `77A9H` | `COMMS_ACTIVATE` | ROM | Activate serial/comms terminal |
| `781DH` | `BATT_LOW_STR` | ROM | Stored 'Warning - batteries are low' message (data) |
| `7875H` | `KBD_REPEAT_STATE` | ROM | Keyboard repeat/debounce state |
| `789AH` | `NSC810_INIT` | ROM | Sets Port C DDR=0x20 on boot (SOUND_DEV.md) |
| `78C6H` | `WARM_FLAG_INIT` | ROM | Set warm-restart flags |
| `78D6H` | `SCROLL_DISP_INIT` | ROM | Scroll-display initialisation |
| `78F3H` | `COLD_INIT` | ROM | Cold-restart initialisation |
| `7938H` | `CLOCK_TICK` | ROM | Software RTC tick |
| `7976H` | `PORT4F_RESET` | ROM | Flush port 4FH then load RAM from ROM constant |
| `7986H` | `ZERO_RANGE` | ROM | Fill [DE..HL] with 0 using SBC-size+LDIR chain |
| `7992H` | `TAPE_POS_CHK` | ROM | Check the current tape position |
| `79B0H` | `INPUT_LINE` | ROM | Line input with editing |
| `7AD1H` | `TEST_MODE_FA56` | ROM | Return Z=1 if mode inactive |
| `7CC6H` | `CHAR_OUT_A` | ROM | Character output (single-byte entry from A) |
| `7CD6H` | `KWD_SCAN_CMP` | ROM | Inner loop of the BASIC keyword scanner |
| `7F07H` | `SERIAL_FLUSH_CHK` | ROM | Check whether the serial output buffer needs to drain |
| `819CH` | `BREAK_SET` | ROM | Power up the RS-232 driver chip (sets the BREAK output) |
| `8394H` | `SERIAL_IO_INIT` | ROM | Serial/comms init |
| `8543H` | `CHK_ASCII_DIGIT` | ROM | Check whether ASCII char A is a digit 0-9 (returns the value) |
| `869CH` | `EVAL_ARG_COMMA` | ROM | Evaluate argument + optional comma |
| `87D1H` | `PARSE_ADDR_ARGS` | ROM | Parse address expression args |
| `8ACFH` | `BASIC_HALT_LOOP` | ROM | Main BASIC idle |
| `8AE4H` | `SERIAL_WAKEUP` | ROM | Wake-up from interrupt when serial activity is detected |
| `8AEDH` | `WARM_SENTINEL_SET` | ROM | Set the warm-restart sentinel |
| `8AF2H` | `CONTEXT_SAVE` | ROM | Save ALL registers + SP to stack (full Z80 context snapshot) |
| `8B17H` | `BASIC_WARM_START` | ROM | BASIC interpreter warm-start / full context restore (EPROM4) |
| `8BA8H` | `KBD_MODE_INIT` | ROM | Keyboard mode init: set RAM=1 |
| `8BE3H` | `ENV_INIT` | ROM | Full environment init (display + keyboard + serial + RTC) |
| `8C04H` | `HW_STARTUP_INIT` | ROM | Hardware startup init (subset of ENV_INIT) |
| `8C28H` | `LCD_RESET_SEQ` | ROM | LCD reset + serial flush sequence |
| `8C38H` | `LCD_HD61830_INIT` | ROM | Initialise the HD61830 LCD controller |
| `8CBBH` | `LCD_ADDR_CALC` | ROM | Compute VRAM byte offset + bit: row×30 (via REPEAT_ADD) + col>>3 = HL |
| `8CD7H` | `LCD_PIXEL_SET` | ROM | Pixel bounds check (H<F0H, L<40H) + LCD_ADDR_CALC + LCD cursor write |
| `8D19H` | `PSET_STMT_HDL` | ROM | PSET/PRESET statement handler |
| `8D72H` | `DRAW_STMT_HDL` | ROM | DRAW statement handler |
| `8E92H` | `LCD_PIXEL_ROW` | ROM | LCD pixel row |
| `8FD8H` | `LINE_HDL` | ROM | LINE statement handler |
| `90A3H` | `LCD_COORD_PARSE` | ROM | LCD coordinate parse |
| `917FH` | `LCD_SET_ADDR` | ROM | Write a 16-bit value to LCD controller address regs 0AH/0BH |
| `9403H` | `REPEAT_ADD` | ROM | Multiply: HL = DE × A (repeated-add) |
| `94BDH` | `CRLF_REPEAT_HDL` | ROM | Handle the BASIC CR/LF repeat sequence |
| `9607H` | `STATE_SAVE_FRAG` | ROM | State save fragment |
| `9711H` | `LIST_LINE_RENDER` | ROM | Render one BASIC listing line: load/save RAM around LIST_DISPLAY_SCAN |
| `971DH` | `LIST_DISPLAY_SCAN` | ROM | Scan the display buffer while rendering a LIST line |
| `9A78H` | `LIST_RENDER_SCREEN` | ROM | Render a full screenful of LIST output |
| `9ADCH` | `DISP_BUF_CHK` | ROM | Check the display buffer is in sync |
| `9B6AH` | `LIST_PAGE_BODY` | ROM | Body of one LIST output page |
| `9C13H` | `PUTCHAR_B7` | ROM | Preset B=7 then dispatch to PUTCHAR |
| `9C7DH` | `CMP_HL_DE` | ROM | Compare HL with DE |
| `9DD8H` | `LIST_FF_EMIT` | ROM | LIST form-feed emit (B=06) |
| `9DF8H` | `STR_EMIT_PAIR` | ROM | Emit a pair of stacked characters |
| `9EE1H` | `LIST_FF_HDR` | ROM | LIST form-feed header (B=0F) |
| `9EFEH` | `LIST_COL_EMIT` | ROM | LIST column prefix emitter |
| `A4AAH` | `PUTCHAR_FF` | ROM | Init the display before form-feed output |
| `A4AFH` | `PUTCHAR_SP` | ROM | Output a space for whitespace padding |
| `A4B3H` | `CHECK_WIDTH_6` | ROM | Check current line width against the limit |
| `A4B9H` | `LIST_COL_INIT` | ROM | Init the LIST column counter |
| `A5BCH` | `FILE_LOAD_BLOCKS` | ROM | LOAD: read a sequence of RAM-disk blocks into memory |
| `A5E2H` | `FILE_SAVE_BLOCKS` | ROM | SAVE: write a memory block out to the RAM-disk |
| `A606H` | `STR_LIT_PARSE` | ROM | String literal parse with blank check |
| `A6B9H` | `STORE_PRAM_DISP` | ROM | LD DE,PRAM_JP_PATCH |
| `A6BCH` | `STORE_DISP_PTR` | ROM | Store 16-bit ptr DE into RAM:RAM (display output pointer pair) |
| `A6C4H` | `PARSE_STR_LIT` | ROM | Parse "..." string literal from program text in HL |
| `A6DDH` | `STR_BUF_INIT` | ROM | Fill 0E05DH with 11 spaces |
| `A754H` | `FILENAME_PARSE` | ROM | Parse "name.ext" from HL: scan '.' |
| `A769H` | `DIR_ENTRY_DISP` | ROM | Print directory entry: load IX from HL |
| `A797H` | `PRINT_CHARS` | ROM | Print B chars from (HL) |
| `A7A1H` | `EXT_BLANK_CHK` | ROM | Check if 3-char extension at E065H is all spaces |
| `A7B8H` | `RAMDISK_READ` | ROM | RAM-disk read entry (OS RST 20 call) |
| `A7BBH` | `RAMDISK_WRITE` | ROM | RAM-disk write entry (OS RST 20 call) |
| `A7BEH` | `RAMDISK_CLOSE` | ROM | RAM-disk close entry (OS RST 20 call) |
| `A7C4H` | `BASIC_ENV_INIT` | ROM | Clear BASIC environment RAM |
| `A7E2H` | `BASIC_REINIT` | ROM | Full BASIC re-initialisation |
| `A808H` | `CMD_PROMPT` | ROM | Main BASIC command REPL |
| `A8D3H` | `EDIT_VECS_LOAD` | ROM | Load the edit-mode paged-RAM vector table |
| `A8FEH` | `PRAM_CHAR_DISP` | ROM | Paged-RAM character + display helper |
| `A9F6H` | `CMD_TABLE_SCAN` | ROM | Scan command table at DE vs tokenised input at HL ( per char) |
| `AACEH` | `SET_TAPE_FLAGS` | ROM | Set the tape activity flags |
| `AADBH` | `SKIP_PARSE_STR` | ROM | Skip / parse a string in the input line |
| `AAFFH` | `SKIP_SPACES` | ROM | Advance HL past 0x20 spaces: while (HL)==20H { INC HL } |
| `AB0DH` | `LINE_BUF_CLEAR` | ROM | Fill E080H..E0FFH (128 bytes) with 0x20 (space) |
| `AB36H` | `TAPE_HDR_BUILD` | ROM | Build tape file header at F87CH |
| `ACBDH` | `SKIP_DISP_OUT` | ROM | Skip spaces + display output |
| `AD71H` | `TAPE_LLOAD` | ROM | Tape LLOAD command handler |
| `ADBBH` | `CMD_DIR` | ROM | DIR command handler |
| `AFC3H` | `PRINT_STR_GATE` | ROM | Print a string through the output gate |
| `B144H` | `SERIAL_ECHO_TEST` | ROM | Send 55H via echo + output paths |
| `B173H` | `TOUPPER` | ROM | Uppercase converter: if A in [61H-7AH] (a-z), RES 5,A (→ A-Z) |
| `B188H` | `OS_MSG_STRINGS` | ROM | DEMOS message/label string table (B188H-B2CAH, data). 00-separated |
| `B2E8H` | `FILE_SET_BLK_PTR` | ROM | File: set the current block pointer |
| `B303H` | `FILE_SAVE_BLK` | ROM | File: save the current block to RAM-disk |
| `B309H` | `FILE_OPEN` | ROM | Dispatch paged RAM call [17] (PRAM_REC_OPEN) |
| `B314H` | `FILE_LOAD_BLK` | ROM | File: load the current block from RAM-disk |
| `B408H` | `LCD_CLR_CMD` | ROM | LCD controller LCD clear cmd pair |
| `B412H` | `LCD_CLR_SCREEN` | ROM | Full screen clear |
| `B42AH` | `RTC_TICK_POLL` | ROM | Watch the real-time clock for a tick and redraw the on-screen clock |
| `B43AH` | `LCD_FONT` | ROM | LCD character font — standard 7-row ASCII glyphs |
| `B6DAH` | `LCD_FONT2` | ROM | LCD character font — taller 9-row alternate glyphs (menus) |
| `E05CH` | `PRAM_STR_BUF` | RAM | Paged RAM string buffer start (dest of ALT_CHAR_OUT 11H path) |
| `E068H` | `PRAM_STR_BUF_B` | RAM | Paged RAM string buffer B (cleared by A5DDH init) |
| `E080H` | `PRAM_JP_PATCH` | RAM | Paged RAM JP trampoline patch target (→D706H, patched with 0C3H) |
| `E373H` | `RST18_DISPATCH` | RAM | BIOS-call dispatcher (RST 18 handler in the E000 window) |
| `E38FH` | `RST20_DISPATCH` | RAM | Paged-RAM call dispatcher (RST 20 handler in the E000 window) |
| `E49AH` | `PAGE_RESTORE` | RAM | Restore paging reg |
| `E4A5H` | `PRAM_PAGE_CTRL` | RAM | Paged RAM page-control alt entry (between PAGE_RESTORE/PAGE_SELECT_0) |
| `E4A9H` | `PAGE_SELECT_0` | RAM | Select page 0 |
| `E5B4H` | `PRAM_CHAR_ECHO` | RAM | Char output (echo path): save AF + paging reg |
| `E5C0H` | `PRAM_CHAR_OUT` | RAM | Char output (normal path): save paging reg |
| `E674H` | `SOUND_CALLBACK` | RAM | Timer-B-driven callback in paged RAM (SOUND_DEV.md) |
| `E72AH` | `PRAM_RST20_OVERLAY` | RAM | Base of the 0x700-byte paged RAM call paged RAM overlay window |
| `E7DEH` | `PRAM_LDIR_12` | RAM | Copy 12 bytes within paged RAM (LDIR helper) |
| `E7E2H` | `PRAM_LDIR_32` | RAM | Copy 32 bytes within paged RAM (LDIR helper) |
| `E7E6H` | `PRAM_LDIR_128` | RAM | Copy 128 bytes within paged RAM (LDIR helper) |
| `E81AH` | `PRAM_REC_OPEN` | RAM | Page→F852H and patch the E080H (PRAM_JP_PATCH) JP trampoline |
| `E837H` | `PRAM_REC_REOPEN` | RAM | Re-open the most-recently-opened record without a name search |
| `E843H` | `PRAM_REC_CREATE` | RAM | NEW named record (scans banks for an 0E5H empty slot). Returns error |
| `E89EH` | `PRAM_REC_SAVE_BLK` | RAM | FILE_SAVE_BLOCKS loop). Stages/advances a record block for writing |
| `E8C8H` | `PRAM_REC_LOAD_BLK` | RAM | FILE_LOAD_BLOCKS loop). Stores/advances a received record block |
| `E908H` | `PRAM_REC_LOOKUP` | RAM | PRAM_REC_SEARCH + EBFDH (finalise) |
| `E941H` | `PRAM_REC_DELETE` | RAM | Delete a record in the paged-RAM file store |
| `EA28H` | `PRAM_REC_POS_INIT` | RAM | Read-cursor state (E07DH/E07EH/E07FH from E068H/E07CH) |
| `EAC8H` | `PRAM_REC_SEARCH` | RAM | Search RAM banks (page 81H+, via 0E7EFH/0E7F5H switch + 0E887H |
| `EADFH` | `PRAM_RET_OK` | RAM | Paged-RAM helper: return success |
| `EAF3H` | `PRAM_REC_MATCH` | RAM | Per-bank match: scan 32-byte (BC=0020H) records from HL=0100H |
| `EB57H` | `PRAM_BLK_READ` | RAM | Read 128 bytes from the current record block (RAM_BLK_PTR) → E080H |
| `EB6BH` | `PRAM_BLK_WRITE` | RAM | Write 128 bytes from E080H → the current record block (RAM_BLK_PTR) |
| `EB7FH` | `PRAM_REC_CLOSE_ALL` | RAM | Walk the open-record context list (RAM_PAGED_CTX/F80BH) calling |
| `EB91H` | `PRAM_CTX_SETUP_OP` | RAM | Paged-RAM named-record store (TODO-3, 2026-05-27). The paged RAM call services operate on a |
| `EB95H` | `PRAM_CTX_SETUP` | RAM | Attribute high-bits in the fetched arg block). Most common entry |
| `EBA8H` | `PRAM_CTX_ARGCOPY` | RAM | Base: save DE→RAM, zero E05CH, then LDIR 0x23 bytes from the |
| `EC48H` | `PRAM_BITMAP_FLUSH` | RAM | Copy the 80-byte block-allocation bitmap from CPU 0040H to its |
| `EC5EH` | `PRAM_BLOCK_ALLOC` | RAM | Allocate a 2 KB data block: scan the 0040H bitmap (80 bytes / 640 |
| `EC9EH` | `PRAM_BLOCK_ADDR` | RAM | Data-block index → byte address (index × 0800H |
| `ECA7H` | `PRAM_BLOCK_FREE` | RAM | Free a 2 KB data block: clear its bit in the allocation bitmap |
| `ED09H` | `PRAM_REC_READ_NEXT` | RAM | Read the next 128-byte chunk of the open record into E080H: advance |
| `ED25H` | `PRAM_BLOCK_ENSURE` | RAM | Write path: ensure the cursor's 2 KB block exists — if not, allocate |
| `ED5CH` | `PRAM_REC_WILD_BEGIN` | RAM | Begin wildcard search: save E068H (name key byte) to RAM and set |
| `ED68H` | `PRAM_REC_WILD_END` | RAM | Restore E068H saved by PRAM_REC_WILD_BEGIN |
| `F403H` | `RAM_TOKEN_BUF` | RAM | Tokenized line buffer |
| `F506H` | `RAM_WORK_BUF` | RAM | Work buffer (paged copy destination, 256-byte block) |
| `F77FH` | `RAM_STACK_TOP` | RAM | Initial/reset stack pointer value (LD SP,RAM at boot/restart) |
| `F780H` | `RAM_CURSOR_STATE` | RAM | Cursor column reg + CHAR_OUT mode flag (bit 6 = gfx path) |
| `F782H` | `RAM_LCD_ADDR` | RAM | LCD VRAM cursor address (LCD controller cursor position, 16-bit) |
| `F799H` | `RAM_KBD_MATRIX` | RAM | RAM keyboard matrix |
| `F7A7H` | `RAM_OUTPUT_SUPPRESS` | RAM | Output suppress flag (non-zero → PUTCHAR_GATE suppresses output) |
| `F7B5H` | `RAM_BASE_PAGE` | RAM | Base ROM page value (bit 7 set → non-maskable interrupt page in PAGE_RESTORE) |
| `F7B7H` | `RAM_MACHINE_TYPE2` | RAM | Machine type mirror (warm-restart copy of RAM_MACHINE_TYPE) |
| `F7C3H` | `RAM_LCD_GATE_C3` | RAM | LCD column-gate flag C3 (set FFH by SET_LCD_GATE_C3) |
| `F7C6H` | `RAM_PAGE_REG` | RAM | Current paging register shadow (written by PAGE_RESTORE) |
| `F7CFH` | `RAM_EXPR_CONTEXT` | RAM | Expression parse context flag (cleared by PARSE_EXPR |
| `F7D2H` | `RAM_ROM_SCAN_PTR` | RAM | ROM data scan pointer (updated during paged copy init) |
| `F7E5H` | `RAM_SERIAL_ACTIVE` | RAM | Tape/serial activity flag (cleared by CLR_TAPE_FLAG) |
| `F804H` | `RAM_GFX_MODE` | RAM | Graphics direct-write mode flag (1 = bypass char routing) |
| `F809H` | `RAM_PAGE_CTX_HL` | RAM | Paged context HL save (address stored at page-select time) |
| `F80BH` | `RAM_PAGED_CTX` | RAM | Paged context pointer/counter (decremented before PRAM_PAGE_CTRL) |
| `F80DH` | `RAM_MACHINE_TYPE` | RAM | Machine type: 0 = base Hunter, 1 = alt-ROM, 2 = expansion |
| `F822H` | `RAM_TX_CHAR` | RAM | Active serial transmit character register |
| `F824H` | `RAM_TX_DISPATCH` | RAM | Serial transmit non-maskable interrupt dispatch byte (next stub low address) |
| `F864H` | `RAM_NMI_PHASE` | RAM | Non-maskable interrupt phase shift register (sound/serial) |
| `F86EH` | `RAM_EXPR_RESULT_PTR` | RAM | Expression result pointer (= RAM_EXPR_BUF at EXPR_INIT) |
| `F87CH` | `RAM_EXPR_BUF` | RAM | Expression output buffer base (9-byte float work area) |
| `F985H` | `RAM_SER_BUF_LIM` | RAM | Serial input buffer limit |
| `F987H` | `RAM_SER_BUF_PTR` | RAM | Serial input buffer pointer |
| `F990H` | `RAM_ICR_ACTIVE` | RAM | Active interrupt mask value (OUT to set interrupt mask |
| `F992H` | `RAM_PAGE_SAVE` | RAM | Saved page register for the PAGE_RESTORE convention (TODO-C, 2026-05-26) |
| `F999H` | `RAM_RX_CHAR_VEC` | RAM | Serial receive per-character dispatch vector (TODO-C3, 2026-05-28) |
| `F99FH` | `RAM_RX_VEC2` | RAM | Second serial dispatch vector, set alongside RAM_RX_CHAR_VEC by the |
| `FA1CH` | `RAM_CURSOR_COL` | RAM | Cursor column (editor RAM |
| `FA1EH` | `RAM_CURSOR_ROW` | RAM | Scroll-row / cursor-row (RAM:RAM pair) |
| `FA20H` | `RAM_WIN_BOUNDS` | RAM | Window bounds (RAM:RAM = col-max:row-max) |
| `FA2CH` | `RAM_LIST_SCAN_POS` | RAM | Saved display position during LIST output (16-bit) |
| `FA35H` | `RAM_PRINT_FLAGS` | RAM | Tested by TEST_PRINT_FLAG |
| `FA38H` | `RAM_DISP_COL_SAVE` | RAM | Saved display column (swapped with RAM around window calls) |
| `FA39H` | `RAM_DISP_COL` | RAM | Current display column counter |
| `FA3BH` | `RAM_DISP_ROW` | RAM | Current display row counter |
| `FA41H` | `RAM_DISP_PTR` | RAM | Display pointer (16-bit) |
| `FA4DH` | `RAM_CPOS_HI` | RAM | Cursor set-position high byte (row) |
| `FA4EH` | `RAM_CPOS_LO` | RAM | Cursor set-position low byte (col) |
| `FA51H` | `RAM_COMMS_ST1` | RAM | Comms terminal state byte 1 (saved/restored by COMMS_ACTIVATE) |
| `FA53H` | `RAM_COMMS_ST3` | RAM | Comms terminal state byte 3 |
| `FA55H` | `RAM_COMMS_ST5` | RAM | Comms terminal state byte 5 |
| `FA7AH` | `RAM_LOAD_ADDR` | RAM | Current load address for Intel HEX / binary load |
| `FA83H` | `RAM_EXPR_MODE` | RAM | Expression mode / token dispatch state byte |
| `FA85H` | `RAM_EXPR_STK_BASE` | RAM | Expression evaluation stack base pointer (16-bit) |
| `FA87H` | `RAM_COMMS_ST7` | RAM | Comms/display state byte 7 (RAM area, near RAM) |
| `FA88H` | `RAM_PARSE_OP` | RAM | BASIC parser operation byte (37H = string op etc.) |
| `FA94H` | `RAM_LCD_GATE_94` | RAM | LCD column-gate flag 94 (set FFH by SET_LCD_GATE_94) |
| `FAA8H` | `RAM_SOUND_STATE` | RAM | SOUND state machine callback pointer (Timer-B-driven FSM) |
| `FAC6H` | `JP_TRAMPOLINE` | RAM | Indirect jump trampoline (re-pointed by SOUND_MODE_INIT) |
| `FCEFH` | `RAM_DISP_VEC_LO` | RAM | Display output vector low byte (STORE_DISP_PTR target) |
| `FCF0H` | `RAM_DISP_VEC_HI` | RAM | Display output vector high byte |
| `FCF9H` | `RAM_CHAR_ROUTE` | RAM | CHAR_OUT routing: 0=text, bit7=gfx, else=alt-window |
| `FCFDH` | `RAM_MENU_CTX` | RAM | Menu context active flag |
| `FDD6H` | `RAM_SCRATCH_FDD6` | RAM | Shared transient scratch slot (TODO-B resolved 2026-05-26) |
| `FDD9H` | `RAM_BLK_PTR` | RAM | Pointer to the current RAM-disk data block |
| `FDFAH` | `RAM_MENU_REENTR` | RAM | Menu re-entrancy guard (L_7BF2H) |
| `FDFBH` | `TIMER_AB_ISR` | RAM | Timer A/B common ISR entry (SOUND_DEV.md / 0xFDFB file) |
| `FE0EH` | `TIMER_AB_ISR_END` | RAM | Timer A/B ISR exit (0xFE0E file) |
| `FE51H` | `RAM_FP_SCRATCH` | RAM | Floating point scratch area (used by POW_OP FLOAT_COPY) |
| `FEF2H` | `RAM_KEY_CHAR_TBL` | RAM | Keyboard character lookup table (112 entries) |
| `FFB4H` | `RAM_PROG_RUNNING` | RAM | BASIC program running flag (non-zero = program executing) |
| `FFC6H` | `RAM_FP_HEAP` | RAM | BASIC floating-point heap pointer |

