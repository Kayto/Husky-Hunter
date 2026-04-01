#!/usr/bin/env python3
"""feed.py — PC-side performance feed for the Husky Hunter.

Reads CPU and memory usage, sends over RS-232 as separate lines.
"""

import argparse
import sys
import time

import psutil
import serial
import serial.tools.list_ports


def list_ports():
    """Print available serial ports."""
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("No serial ports found.")
        return
    for p in ports:
        print(f"  {p.device:10s}  {p.description}")


def feed(port: str, baud: int, interval: float):
    """Main feed loop: read CPU/MEM, send over serial."""
    print(f"Opening {port} at {baud} baud...")
    try:
        ser = serial.Serial(port, baud, timeout=1)
    except serial.SerialException as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Feeding CPU%,MEM% every {interval:.1f}s  (Ctrl+C to stop)")
    print()

    try:
        psutil.cpu_percent(interval=0.1)

        while True:
            cpu = int(psutil.cpu_percent(interval=None))
            mem = int(psutil.virtual_memory().percent)

            cpu = max(0, min(100, cpu))
            mem = max(0, min(100, mem))

            ser.write(f"{cpu}\r\n".encode("ascii"))
            ser.write(f"{mem}\r\n".encode("ascii"))

            print(f"\r  CPU: {cpu:3d}%   MEM: {mem:3d}%", end="", flush=True)

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\nStopped.")
    finally:
        ser.close()


def main():
    parser = argparse.ArgumentParser(
        description="Feed CPU/MEM data to Husky Hunter file logger"
    )
    parser.add_argument(
        "-p", "--port",
        help="Serial port (e.g. COM3, /dev/ttyUSB0)"
    )
    parser.add_argument(
        "-b", "--baud", type=int, default=4800,
        help="Baud rate (default: 4800)"
    )
    parser.add_argument(
        "-i", "--interval", type=float, default=1.0,
        help="Sample interval in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List available serial ports and exit"
    )

    args = parser.parse_args()

    if args.list:
        list_ports()
        sys.exit(0)

    if not args.port:
        print("Error: --port is required (use --list to see available ports)",
              file=sys.stderr)
        sys.exit(1)

    feed(args.port, args.baud, args.interval)


if __name__ == "__main__":
    main()
