# Husky HCOM for Windows

A "modern" launcher for HCOM — the file transfer utility for Husky handheld computers (Hunter, Hunter 2, Hawk, Hunter 16, FS/2).

This package runs HCOM on modern 64-bit Windows using [DOSBox](https://www.dosbox.com) to emulate the DOS environment, with an interactive launcher that handles all configuration.

> **Disclaimer:** This software is provided as-is with no warranty. The authors accept no responsibility for data loss or damage to your Husky device. **Always back up important data on your Hunter before syncing.**

---

## Requirements

- **Windows 7 or later** (64-bit)
- **DOSBox 0.74+** — free download from [dosbox.com](https://www.dosbox.com)
- **USB-to-Serial adapter** (FTDI or Prolific chipset recommended)
- **RS-232 serial cable** for your Husky device

---

## Installation

### Step 1 — Install DOSBox

Download and install DOSBox from [dosbox.com](https://www.dosbox.com) (default install location is fine).

### Step 2 — Download the HCOM files

Download the original **HCOMW** distribution zip from:

> **[https://github.com/TheEPROM9/Husky-Computer-ROM-Images/blob/main/hcomw.zip](https://github.com/TheEPROM9/Husky-Computer-ROM-Images/blob/main/hcomw.zip)**

(Click the **Download** button on the right-hand side of the page.)

Extract `hcomw.zip` into this folder — the zip contains a `hcomw\` directory with all the HCOM files. Then place the launcher files alongside it.

The final folder structure should look like this:

```
HuskyHCOM\
  LaunchHCOM.bat          ← Double-click this to start
  LaunchHCOM.ps1          ← Launcher script (do not edit)
  SyncToHunter.bat        ← Dev sync launcher
  SyncToHunter.ps1        ← Dev sync script
  README.md               ← This file
  hcomw\                  ← Extracted from hcomw.zip (do not modify)
    HCOM.DOS\
      HCOM.EXE
      HCOM.CFG
      HCOM.HLP
      CMDHCOM.EXE
      CMDHCOM.CFG
      HCS.COM
      ... (other support files)
    HUNTER.BI_            ← Original installer files (can be ignored)
    HAWK.BI_
    H16FS2.BI_
    HCOMW.EX_  etc.
  HSYNC\                 ← Your sync files (created on first sync)
```

---

## First Run

1. **Double-click `LaunchHCOM.bat`**

2. The launcher guides you through three steps:

   **Step 1 — DOSBox Location**
   It will auto-detect DOSBox if installed in the default location. Confirm with `Y`, or enter the full path to `DOSBox.exe` manually.

   **Step 2 — Device Type**
   Select your Husky handheld model. This sets the correct baud rate automatically:

   | Device | Baud Rate |
   |--------|-----------|
   | Hunter / Hunter 2 | 4800 |
   | Hawk | 19200 |
   | Hunter 16 / Hunter 16/80 | 38400 |
   | FS/2 | 38400 |

   **Step 3 — Serial Port**
   The launcher detects available COM ports and shows them with their description (e.g. "USB Serial Port"). Select your USB-to-Serial adapter.

3. **HCOM launches inside DOSBox.** Your settings are saved for next time.

---

## Using HCOM

HCOM shows two panels: local PC files (left) and remote Husky files (right).

### Key Commands

| Key | Action |
|-----|--------|
| `C` | Connect to Husky (HCOM must be running on the Husky too) |
| `T` | Transfer tagged/highlighted files |
| `D` | Delete tagged/highlighted files |
| `L` | Switch disk drive (PC or Husky) |
| `S` | Download firmware to Husky |
| `A` | Sync Husky clock to PC time |
| `R` | Exit HCOM on the Husky |
| `O` | Options menu (COM port, baud rate, etc.) |

### Navigation

| Key | Action |
|-----|--------|
| Arrow keys | Move selection |
| Enter | Tag / untag file |
| Ctrl+Enter | Tag all / untag all |
| Tab | Switch between PC and Husky panels |
| ESC or Q | Quit |

---

## Subsequent Launches

Just double-click `LaunchHCOM.bat`. It remembers your DOSBox location and device type. It will ask you to confirm the COM port each time (in case the adapter moved to a different port).

To reconfigure device type or DOSBox path:

```
LaunchHCOM.bat --setup
```

---

## Dev Sync Workflow

If you develop software for the Hunter, `SyncToHunter.bat` provides fully automated sync using CMDHCOM commands — no manual HCOM interaction needed.

### Setup

1. Run `LaunchHCOM.bat` at least once to configure DOSBox and serial port settings.
2. Double-click `SyncToHunter.bat` for the first time.

### First run — download from Hunter

On first run (empty `HSYNC\` and no manifest), the script will:

1. Ask for confirmation, then automatically run `CMDHCOM /RX=*.*` to download all files from the Hunter
2. DOSBox opens briefly while the transfer runs, then closes automatically
3. Detect the downloaded files, move them into `HSYNC\`, and create the initial sync manifest

After this, `HSYNC\` mirrors the Hunter's contents and change tracking begins.

### Subsequent runs — push changes

Double-click `SyncToHunter.bat` (or run from a command prompt). It will:

1. **Compare** `HSYNC\` against the last sync manifest
2. **Show a summary** of new, modified, and deleted files
3. **For deleted files**, prompt you per file:
   - **D** = Delete from Hunter
   - **R** = Re-download from Hunter back to HSYNC
   - **S** = Skip (remove from tracking, leave on Hunter)
4. **Build a CMDHCOM batch** with the appropriate commands
5. **Run DOSBox** which executes the batch automatically — DOSBox opens briefly, then closes
6. **Update the manifest** and clean up staged files

### Typical workflow

1. Edit files in `HSYNC\`
2. Run `SyncToHunter.bat`
3. Review the change summary, press `Y` to sync
4. Wait for DOSBox to complete the transfer (a few seconds)
5. Done — manifest is updated automatically

### Notes

- **Back up your Hunter data before syncing.** This tool deletes and overwrites files on the device.
- Make sure the Hunter is connected, powered on, and running HCOM before syncing.
- Filenames must be **DOS 8.3 compatible** (max 8 chars + 3 char extension). The script will warn you if any aren't.
- The script won't overwrite HCOM program files — it blocks filenames like `HCOM.EXE`, `CMDHCOM.EXE`, etc.
- Modified files are handled by deleting the old version on the Hunter first, then uploading the new one.
- The sync manifest is stored in `hunter-sync.manifest` — delete it to start fresh.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **"No COM ports detected"** | Plug in your USB-to-Serial adapter. Check Device Manager to confirm it has a COM port. Install the adapter's driver if needed. |
| **"Serial Port could not be opened"** | Make sure no other program is using the COM port. Close any other serial terminal software. Try unplugging and re-plugging the adapter. |
| **HCOM says "No remote attached"** | Check the serial cable connection. Make sure HCOM is running on the Husky. Verify the baud rate matches your device type (press `O` in HCOM to check). |
| **DOSBox window closes immediately** | Run `LaunchHCOM.bat` from a command prompt to see error messages. |
| **Wrong baud rate** | Run `LaunchHCOM.bat --setup` and select the correct device type. |

---

## Supported Devices

| Device | Baud Rate | Firmware File |
|--------|-----------|---------------|
| Husky Hunter | 4800 | `HUNTER.BIN` |
| Husky Hunter 2 | 4800 | `HUNTER.BIN` |
| Husky Hawk | 19200 | `HAWK.BIN` |
| Husky Hunter 16 | 38400 | `H16FS2.BIN` |
| Husky Hunter 16/80 | 38400 | `H16FS2.BIN` |
| Husky FS/2 | 38400 | `H16FS2.BIN` |

---

## Files in This Package

| File | Description |
|------|-------------|
| `LaunchHCOM.bat` | Windows launcher (double-click this) |
| `LaunchHCOM.ps1` | PowerShell setup/launch script |
| `SyncToHunter.bat` | Dev sync launcher |
| `SyncToHunter.ps1` | Dev sync script |
| `README.md` | This file |
| `HSYNC\` | Your sync files (created on first sync run) |
| `hcomw\HCOM.DOS\HCOM.EXE` | Interactive file manager |
| `hcomw\HCOM.DOS\HCOM.CFG` | HCOM configuration |
| `hcomw\HCOM.DOS\HCOM.HLP` | HCOM help file |
| `hcomw\HCOM.DOS\CMDHCOM.EXE` | Command-line transfer tool |
| `hcomw\HCOM.DOS\CMDHCOM.CFG` | CMDHCOM configuration |
| `hcomw\HCOM.DOS\HCS.COM` | HCOM communications server |
| `hcomw\HCOM.DOS\HUNTER.BIN` | Hunter / Hunter 2 firmware |
| `hcomw\HCOM.DOS\HAWK.BIN` | Hawk firmware |
| `hcomw\HCOM.DOS\H16FS2.BIN` | Hunter 16 / FS/2 firmware |

Auto-generated at runtime (not included in the distribution):

| File | Description |
|------|-------------|
| `hcom-settings.ini` | Saved user preferences |
| `dosbox-hcom.conf` | DOSBox hardware configuration |
| `dosbox-hcom-autoexec.conf` | DOSBox HCOM launch commands |
| `hunter-sync.manifest` | Dev sync tracking (what was last synced) |

---

## Credits

- **HCOM software:** Copyright Husky Computers Limited
- **DOSBox:** Copyright 2002–2019 DOSBox Team ([GNU GPL](https://www.dosbox.com))
- **Launcher scripts:** By Kayto 28/03/2026

---

## License

The launcher scripts are licensed under the [MIT License](LICENSE).

> **Disclaimer:** This software is provided as-is with no warranty of any kind. The authors accept no responsibility for data loss, damage to hardware, or any other issues arising from use of this software. **Always back up important data on your Husky device before syncing.**
