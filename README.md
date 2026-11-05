# Kowalski — Windows Crash Investigator

**Version 1.1.0** — a local-first, native desktop Windows PC diagnostics app built with Python, PySide6 (Qt) and psutil.

## Features

- Live CPU, RAM, disk and basic system health snapshot.
- Windows Application Error 1000, Windows Error Reporting 1001 and Application Hang 1002 — including many game crashes.
- Windows BugCheck, common BSOD stop codes, Kernel-Power 41, WHEA hardware events and GPU driver timeouts.
- Readable explanations, possible causes and safe troubleshooting suggestions.
- Find Windows minidump files, without claiming to identify a driver from the filename.
- Search crash findings by app name or error code.
- Export JSON or TXT reports, and open built-in Windows maintenance utilities after confirmation.
- No telemetry or required cloud connection.

**Important:** Event Log entries are clues, not confirmed root causes. This release does **not** parse binary memory dumps using WinDbg; it cannot guarantee that every crash is detected or fixed.

## Run from source

On **64-bit Windows 10/11** with Python 3.11:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

## Build a portable Windows app

The workflow at `.github/workflows/windows-build.yml` runs unit tests and an offscreen Qt smoke test on a GitHub-hosted Windows runner and builds the application using PyInstaller.

Visit **Actions → Build Kowalski for Windows → latest successful run → Artifacts → Kowalski-Windows-x64**.

After downloading and extracting the build artifact, extract `Kowalski-Windows-x64.zip`. Run `Kowalski.exe` with all the accompanying files in the folder.

Manual build:

```powershell
python -m pip install pyinstaller==6.16.0
python -m PyInstaller --noconfirm --clean --windowed --onedir --name Kowalski main.py
```

## Testing

```powershell
python -m unittest discover -s tests -v
```

The GitHub Windows runner is not a substitute for testing on Windows machines with real game crashes, BSOD minidumps and different hardware configurations.

## Safety and privacy

Scans do not delete or modify user files. Maintenance controls launch official Windows tools rather than automatically making destructive changes. Reports contain machine names, paths and log messages, so inspect them before sharing. Portable EXEs are unsigned and may display SmartScreen warnings; do not bypass protections on software you cannot verify. Further real Windows testing and an installer remain release tasks.

## Roadmap

- WinDbg-based minidump and driver stack analysis, with symbols and clear confidence ratings
- Crash-time GPU/RAM/temperature correlation where supported
- Guided troubleshooting workflows and full installer
