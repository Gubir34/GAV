import os
import platform
from tqdm import tqdm
import hashlib
import sqlite3

# --- SETTINGS ---
DBS = {
    "SHA256": "signatures_sha256.db",
    "SHA1": "signatures_sha1.db",
    "MD5": "signatures_md5.db",
}

# --- DB bağlan ---
connections = {algo: sqlite3.connect(db) for algo, db in DBS.items()}

def file_hash(path, algo):
    h = hashlib.new(algo.lower())
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def get_drives():
    if platform.system() == "Windows":
        import string
        from ctypes import windll
        bitmask = windll.kernel32.GetLogicalDrives()
        drives = [f"{ltr}:\\" for i, ltr in enumerate(string.ascii_uppercase) if bitmask >> i & 1]
        return drives
    return ["/"]

def iter_files(base):
    for root, dirs, files in os.walk(base, topdown=True, followlinks=False):
        for name in files:
            yield os.path.join(root, name)

# --- INPUT ---
target = input("Enter folder or drive to scan (e.g., C:\\ or /): ").strip()
targets = get_drives() if target == "/" else [target]

# --- 1) ÖN TARAMA: Dosya toplama + ilerleme ---
print("[*] Indexing files...")
all_files = []
for t in targets:
    for f in tqdm(iter_files(t), desc=f"Indexing {t}", unit="file"):
        all_files.append(f)

print(f"[+] Total files: {len(all_files)}")

# --- 2) VİRÜS TARAMASI: İlerleme çubuğuyla hash kontrol ---
print("[*] Scanning files...")
for fpath in tqdm(all_files, desc="Scanning", unit="file"):
    try:
        for algo, conn in connections.items():
            h = file_hash(fpath, algo)
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM signatures WHERE hash=?", (h,))
            if cur.fetchone():
                print(f"[!] Threat detected: {fpath} -> {h} ({algo})")
                break
    except Exception:
        # izin hatası vs. varsa atla
        continue

for conn in connections.values():
    conn.close()

print("[+] Scan finished.")
