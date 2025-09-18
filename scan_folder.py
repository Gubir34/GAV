import hashlib
import pathlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

DB_FILES = {
    "SHA256": "signatures_sha256.db",
    "SHA1": "signatures_sha1.db",
    "MD5": "signatures_md5.db"
}

HASH_ALGOS = {
    "SHA256": "sha256",
    "SHA1": "sha1",
    "MD5": "md5"
}

def hash_file(path, algo="sha256", chunk_size=4*1024*1024):
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()

def load_hashes(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT hash FROM signatures")
    s = set(r[0] for r in cur.fetchall())
    conn.close()
    return s

def scan_folder(folder):
    folder_path = pathlib.Path(folder)
    files = [fp for fp in folder_path.rglob("*") if fp.is_file()]
    print(f"[+] Toplam dosya: {len(files)}. Tarama başlıyor...")

    # her algo için hash setleri
    db_hashes = {algo: load_hashes(db) for algo, db in DB_FILES.items()}

    matches = []

    def check_file(fp):
        result = []
        for algo_name, algo_hash in HASH_ALGOS.items():
            try:
                h = hash_file(fp, algo_hash)
            except:
                continue
            if h in db_hashes[algo_name]:
                result.append((str(fp), h, algo_name))
        return result

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(check_file, fp): fp for fp in files}
        for fut in tqdm(as_completed(futures), total=len(futures), unit="dosya"):
            res = fut.result()
            if res:
                matches.extend(res)
                for fp, h, algo in res:
                    print(f"[!] Zararlı tespit edildi: {fp} -> {h} ({algo})")

    return matches

if __name__ == "__main__":
    import sys
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    matches = scan_folder(folder)
    print(f"\n[+] Tarama bitti. Toplam eşleşme: {len(matches)}")
