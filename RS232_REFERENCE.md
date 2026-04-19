# RS-232 Serial Configuration Reference

The Hunter's serial port is configured at runtime via POKE to fixed memory addresses.
This is required for any program that communicates over RS-232.

## Baud Rate

| Address | Name | Purpose |
| ------- | ---- | ------- |
| 63480 | TXSPEED | Transmit baud rate |
| 63481 | RXSPEED | Receive baud rate |

| Value | Baud |
| ----- | ---- |
| 1 | 75 |
| 2 | 110 |
| 3 | 150 |
| 4 | 300 |
| 5 | 600 |
| 6 | 1200 |
| 7 | 1800 |
| 8 | 2400 |
| 9 | 4800 |

## Parity

| Address | Name | Purpose |
| ------- | ---- | ------- |
| 63487 | TXPTY | Transmit parity |
| 63488 | RXPTY | Receive parity |

| Value | Parity |
| ----- | ------ |
| 0 | None |
| 1 | Odd |
| 2 | Even |

## Handshaking & Protocol

| Address | Name | Purpose | Values |
| ------- | ---- | ------- | ------ |
| 63482 | CTSAF | CTS enable | 0 = No, 1 = Yes |
| 63483 | DTRAF | DTR enable | 0 = No, 1 = Yes |
| 63484 | RTSAF | RTS enable | 0 = No, 1 = Hold, 2 = True |
| 63485 | DSRAF | DSR enable | 0 = No, 1 = Yes |
| 63486 | DCDAF | DCD enable | 0 = No, 1 = Yes |
| 63489 | TXPROT | TX protocol | 0 = None |
| 63493 | RXPROT | RX protocol | 0 = None |

## Serial I/O in BASIC

| Command | Direction | Description |
| ------- | --------- | ----------- |
| `LINPUT "",A$` | Receive | Blocking read from RS-232 until CR received; empty prompt suppressed |
| `LINPUT "",V` | Receive | Blocking read of numeric value from RS-232 |
| `LPRINT` | Transmit | Send string to RS-232 |
| `LOPCHR n` | Transmit | Send single character (ASCII code n) to RS-232 |
| `LINCHR` | Receive | Read single character from RS-232 |
| `ON COM GOSUB n` | Event | Set interrupt handler for incoming serial data (fires on first byte) |
| `COM ON` / `COM OFF` / `COM STOP` | Control | Enable, disable, or pause the COM interrupt |

`LINPUT` blocks until a complete CR-terminated line arrives. There is no timeout mechanism.

**Note:** The Hunter's RS-232 receive buffer is small (~25–32 bytes). Lines longer than this will be truncated by `LINPUT`. Keep individual transmissions short — send one field per line rather than long composite records.

## Examples

### 4800 baud, no parity (PC feed)

```basic
POKE 63480,9:POKE 63481,9   :REM TX/RX baud = 4800
POKE 63482,0                 :REM CTS = No
POKE 63493,0                 :REM RX protocol = None
```

Used by: [performance_log](Progs/performance_log/), [log_file](Progs/log_file/), [news_feed](Progs/news_feed/)

### 1200 baud, odd parity (Zeiss Elta total station)

```basic
POKE 63480,6:POKE 63481,6   :REM TX/RX baud = 1200
POKE 63487,1:POKE 63488,1   :REM TX/RX parity = Odd
POKE 63482,0                 :REM CTS = No
POKE 63493,0                 :REM RX protocol = None
```

Used by: [Dev/elta](Dev/elta/)

### 4800 baud, full handshaking (HCOM file transfer)

```basic
POKE 63480,9:POKE 63481,9   :REM TX/RX baud = 4800
POKE 63482,1                 :REM CTS = Yes
POKE 63484,1                 :REM RTS = Hold
POKE 63487,0:POKE 63488,0   :REM Parity = None (8-bit)
```

Used by: HCOM / File Manager comms setup
