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

## Graphical Interfaces

Both GUIs use the same scan engine (`gav_core.py`) and the translations in `lng.ltf`. Build the signature databases first (run the launcher once).

### GTK 4 (Linux)

```bash
sudo apt install python3-gi gir1.2-gtk-4.0   # Fedora: python3-gobject gtk4
python3 gui_gtk.py              # optional: --lang tr  /path/to/scan
```

### WinUI 3 (Windows 10 1809+)

Requires the .NET 8 SDK and Python 3 (`py` launcher) on `PATH`.

```powershell
dotnet build winui\GavWinUI\GavWinUI.csproj -c Release -p:Platform=x64
winui\GavWinUI\bin\x64\Release\net8.0-windows10.0.19041.0\win-x64\GAV.exe
```

The app finds `gav_core.py` by walking up from its own folder; set `GAV_HOME` if you move the executable elsewhere.

### Engine CLI

`python gav_core.py <folder>` prints results, and `--json` emits one JSON event per line (`start`, `progress`, `threat`, `error`, `done`, `fatal`). The exit code is 1 when threats are found and 2 when there are no signatures.

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
