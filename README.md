# GAV Antivirus

**GAV** is a lightweight, Python-based antivirus tool that scans files and drives using **SHA256**, **SHA1**, and **MD5** hashes.  

---

## Features

- Supports **SHA256**, **SHA1**, and **MD5** hash algorithms  
- Handles **large hash databases** efficiently  
- **Parallel scanning** with multiple threads  
- Shows a **real-time progress bar** via `tqdm`  
- Can scan a **single drive** or **all connected drives**  
- Automatically removes **duplicate hashes** during database compilation  
- Compatible with **Windows** (for now)

---

## Installation

1. Clone or download this repository.  
2. Make sure you have **Python 3.13+** installed.

---

## Usage

1. Open **PowerShell** or **CMD** and navigate to the project folder:

   ```powershell
   cd C:\Users\YourUser\Desktop\GAV
   ```

2. Download the database  
   [Download Database (182 MB)](https://www.dropbox.com/scl/fi/vh12opwwnigvl9f0v9fqp/hashes_raw.txt?rlkey=bwzdy2shcjjfoqeias1hb2mzc&st=t7n3hktp&dl=1)  
   Place the `.txt` file in the main folder (where `launch.py`, `scan_folder.py`, etc. are located).

3. Run the launcher:

   ```powershell
   py launch.py
   ```

---

### What the Launcher Does

1. **Recompiles hashes** (`recompile.py`) → removes duplicates and separates SHA256, SHA1, MD5  
2. **Imports hashes** into databases (`import_hashes.py`)  
3. **Scans** selected directories (`scan_folder.py`)  

When prompted, enter the directories to scan:

- `/` → scan all drives  
- `C:` → scan only the C drive  
- Or specify any other folder path

During scanning, a progress bar appears and detected threats are printed:

```
[!] Threat detected: C:\example\malware.exe -> 8b3f191819931d1f2cef7... (SHA256)
```

---

## Architecture

| Part | Language | What it does |
|---|---|---|
| `GavCore/` | C++17 | Scan engine: multi-threaded SHA256/SHA1/MD5 in one pass, safe file access, signature lookup |
| `gav_core.py`, `scan_folder.py`, `gui_gtk.py`, `launch.py` | Python | Python client of the engine, CLI, GTK 4 GUI, hash DB tooling |
| `winui/GavWinUI/` | C# | WinUI 3 GUI for Windows |

The front-ends talk to the engine over a JSON-lines protocol, so each one can be swapped out without touching the others.

### Building GavCore

Linux (needs OpenSSL and SQLite headers):

```bash
sudo apt install cmake libssl-dev libsqlite3-dev
cmake -S GavCore -B GavCore/build -DCMAKE_BUILD_TYPE=Release
cmake --build GavCore/build
```

Windows (Visual Studio 2022 with C++; uses CNG and the system `winsqlite3`, no extra libraries):

```powershell
cmake -S GavCore -B GavCore\build
cmake --build GavCore\build --config Release
```

Usage: `gavcore [--json] [--db-dir DIR] [--threads N] [--] <path>`. With `--json` it prints one event per line (`start`, `progress`, `threat`, `error`, `done`, `fatal`). Exit codes: 0 clean, 1 threats found, 2 no signatures, 130 cancelled. Without `--db-dir` it looks for the databases next to the executable and then in its parent folders.

## Graphical Interfaces

Build GavCore and the signature databases first (run the launcher once).

### GTK 4 (Linux)

```bash
sudo apt install python3-gi gir1.2-gtk-4.0   # Fedora: python3-gobject gtk4
python3 gui_gtk.py              # optional: --lang tr  /path/to/scan
```

### WinUI 3 (Windows 10 1809+)

Build GavCore first, then build the app with Visual Studio 2022 (the ".NET desktop development" and "Windows App SDK" workloads) or from a Developer PowerShell. `dotnet build` does not work for WinUI 3:

```powershell
msbuild winui\GavWinUI\GavWinUI.csproj /restore /p:Configuration=Release /p:Platform=x64
winui\GavWinUI\bin\x64\Release\net8.0-windows10.0.19041.0\win-x64\GAV.exe
```

`gavcore.exe` is copied next to `GAV.exe`, so no Python is needed. The app finds `lng.ltf` and the databases by walking up from its own folder. Set `GAV_HOME` (and optionally `GAVCORE`) if you move it elsewhere.

---

## Database Files

- `signatures_sha256.db` → stores SHA256 hashes  
- `signatures_sha1.db` → stores SHA1 hashes  
- `signatures_md5.db` → stores MD5 hashes

---

## Notes

- For large scans, running on **SSD drives** or using **multiple CPU threads** speeds up the process.  
- Ensure all dependencies are installed before running.  
- If this project is no longer maintained, you can collect your own MD5/SHA1/SHA256 virus hashes from [MalwareBazaar](https://bazaar.abuse.ch) and add them to `hashes_raw.txt`.

---
