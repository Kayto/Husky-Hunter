#!/usr/bin/env python3
"""feed.py — BBC News RSS feed for the Husky Hunter.

Fetches BBC News headlines, formats to 40 columns, sends over RS-232.
"""

import argparse
import sys
import textwrap
import time
import urllib.request
import xml.etree.ElementTree as ET

import serial
import serial.tools.list_ports

RSS_URL = "https://feeds.bbci.co.uk/news/rss.xml?edition=uk"
WIDTH = 40  # Hunter text columns


def list_ports():
    """Print available serial ports."""
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("No serial ports found.")
        return
    for p in ports:
        print(f"  {p.device:10s}  {p.description}")


def sanitize(text):
    """Convert text to ASCII-safe string for the Hunter."""
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "--")
    text = text.replace("\u2026", "...")
    # LINPUT treats commas as field separators — remove them
    text = text.replace(",", " ")
    return text.encode("ascii", errors="replace").decode("ascii")


def fetch_headlines(url):
    """Fetch RSS feed and return list of (title, description) tuples."""
    req = urllib.request.Request(
        url, headers={"User-Agent": "HuskyHunterNewsFeed/1.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    root = ET.fromstring(data)
    items = []
    for item in root.findall(".//item"):
        title = item.findtext("title", "").strip()
        desc = item.findtext("description", "").strip()
        if title:
            items.append((sanitize(title), sanitize(desc)))
    return items


def format_screen(index, total, title, description):
    """Format a single headline as 8 lines of WIDTH chars."""
    lines = []

    # Row 0: header + counter
    header = "BBC News"
    counter = f"{index}/{total}"
    pad = WIDTH - len(header) - len(counter)
    lines.append(header + " " * max(1, pad) + counter)

    # Row 1: separator
    lines.append("-" * WIDTH)

    # Rows 2-4: title (word-wrapped, max 3 lines)
    tw = textwrap.wrap(title, WIDTH) or [""]
    for i in range(3):
        if i < len(tw):
            text = tw[i]
            if i == 2 and len(tw) > 3:
                text = text[: WIDTH - 3].rstrip() + "..."
            lines.append(text)
        else:
            lines.append("")

    # Row 5: blank separator
    lines.append("")

    # Rows 6-7: description (word-wrapped, max 2 lines)
    dw = textwrap.wrap(description, WIDTH) or [""]
    for i in range(2):
        if i < len(dw):
            text = dw[i]
            if i == 1 and len(dw) > 2:
                text = text[: WIDTH - 3].rstrip() + "..."
            lines.append(text)
        else:
            lines.append("")

    return lines


def feed(port, baud, interval, url):
    """Main feed loop: fetch RSS, send formatted headlines over serial."""
    print(f"Fetching {url} ...")
    headlines = fetch_headlines(url)
    print(f"Got {len(headlines)} headlines.")

    if not headlines:
        print("No headlines found.", file=sys.stderr)
        sys.exit(1)

    print(f"Opening {port} at {baud} baud...")
    try:
        ser = serial.Serial(port, baud, timeout=1)
    except serial.SerialException as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Sending headlines every {interval:.0f}s  (Ctrl+C to stop)")
    print()

    try:
        idx = 0
        while True:
            title, desc = headlines[idx]
            screen = format_screen(idx + 1, len(headlines), title, desc)

            for line in screen:
                ser.write(f"{line}\r\n".encode("ascii", errors="replace"))

            print(f"\r  [{idx+1}/{len(headlines)}] {title[:60]:<60s}",
                  end="", flush=True)

            idx = (idx + 1) % len(headlines)

            # Re-fetch when we've cycled through all headlines
            if idx == 0:
                print(f"\n  Refreshing feed...")
                try:
                    new = fetch_headlines(url)
                    if new:
                        headlines = new
                        print(f"  Got {len(headlines)} headlines.")
                    else:
                        print("  No items returned, reusing cached.")
                except Exception as e:
                    print(f"  Refresh failed: {e} (reusing cached)")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\nStopped.")
    finally:
        ser.close()


def main():
    parser = argparse.ArgumentParser(
        description="Feed BBC News headlines to Husky Hunter"
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
        "-i", "--interval", type=float, default=15.0,
        help="Seconds per headline (default: 15)"
    )
    parser.add_argument(
        "-u", "--url", default=RSS_URL,
        help="RSS feed URL (default: BBC News UK)"
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

    feed(args.port, args.baud, args.interval, args.url)


if __name__ == "__main__":
    main()
