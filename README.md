# GAV Antivirus

GAV is a lightweight, Python-based antivirus tool that can scan files and drives using **SHA256**, **SHA1**, and **MD5** hashes. It supports large hash databases, parallel scanning, and displays a progress bar during scans.

---

## Features

- Supports **SHA256, SHA1, and MD5** hash algorithms
- Handles **large hash databases** efficiently
- **Parallel scanning** using multiple threads
- Shows a **real-time progress bar** using `tqdm`
- Can scan a **single drive** or **all connected drives**
- Automatically removes **duplicate hashes** during database compilation
- Compatible with **Windows** for now :)

---

## Installation

1. Clone or download this repository.
2. Ensure you have **Python 3.13+** installed.


## Usage

1. Open PowerShell or CMD and navigate to the project folder:

"cd C:\Users\YourUser\Desktop\GAV"

2. Download Database(182mb) "https://e.pcloud.link/publink/show?code=XZ5kyUZfLdNkWs9XvJPYfPoKJDnXFvqe1gV" and place the txt file to the main folder that has launch.py scan_folder.py etc.


3. Run the launcher:

"py launch.py"


 # The launcher will:

1. Recompile hashes (recompile.py) → removes duplicates and separates SHA256, SHA1, MD5

2. Import hashes into databases (import_hashes.py)

3. Scan selected directories (scan_folder.py)

4. When prompted, enter the directories to scan:

 / → scan all drives

 C: → scan only the C drive

 Or specify any other folder path

During scanning, a progress bar will be shown, and detected threats will be printed:

[!] Threat detected: C:\example\malware.exe -> 8b3f191819931d1f2cef7... (SHA256)

# Database Files

signatures_sha256.db → stores SHA256 hashes

signatures_sha1.db → stores SHA1 hashes

signatures_md5.db → stores MD5 hashes

# Notes

For large scans, running on SSD drives or using multiple CPU threads speeds up the process.

Ensure all dependencies are installed before running.

This antivirus detects threats only by hash matching at the moment.

When this project isnt maintained by anyone, you can just download your own md5 sha1 and sha256 virus files frome MalwareBazaar and add them to the hashes_raw.txt.

