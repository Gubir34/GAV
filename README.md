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
   [Download Database (182 MB)](https://e.pcloud.link/publink/show?code=XZ5kyUZfLdNkWs9XvJPYfPoKJDnXFvqe1gV)  
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
