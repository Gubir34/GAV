import os
import hashlib
import sqlite3
from lang_loader import LangLoader
from tqdm import tqdm

# Dil yükleyici
lang = LangLoader("lng.ltf", default="en")

# Veritabanı dosyaları
DB_FILES = {
    "SHA256": "signatures_sha256.db",
    "SHA1": "signatures_sha1.db",
    "MD5": "signatures_md5.db"
}

def load_virus_hashes():
    """Veritabanındaki tüm hashleri yükle"""
    virus_db = set()
    for db_file in DB_FILES.values():
        if not os.path.exists(db_file):
            continue
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        try:
            cur.execute("SELECT hash FROM signatures")
            rows = cur.fetchall()
            virus_db.update([row[0] for row in rows])
        except sqlite3.OperationalError:
            pass  # tablo yoksa atla
        conn.close()
    return virus_db

def compute_hashes(file_path):
    """Dosyanın SHA256 hashini hesapla (örnek olarak SHA256 kullanılıyor)"""
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return hashlib.sha256(data).hexdigest()
    except Exception:
        return None

def scan_folder(folder):
    """Klasörü tarar ve hash kontrolü yapar"""
    virus_db = load_virus_hashes()
    all_files = []
    for root, dirs, files in os.walk(folder):
        for f in files:
            all_files.append(os.path.join(root, f))

    if not all_files:
        print(lang.t("no_files"))
        return

    pbar = tqdm(total=len(all_files), bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')
    for file in all_files:
        h = compute_hashes(file)
        if h and h in virus_db:
            tqdm.write(lang.t("threat_detected", file=file, hash=h))
        pbar.update(1)
        pbar.set_description(lang.t("scan_progress", progress=int(pbar.n / len(all_files) * 100)))
    pbar.close()
    print(lang.t("scan_done"))

if __name__ == "__main__":
    import sys
    folder = sys.argv[1] if len(sys.argv) > 1 else input(lang.t("scan_prompt") + ": ")
    if not os.path.exists(folder):
        print(lang.t("invalid_path", path=folder))
    else:
        scan_folder(folder)
