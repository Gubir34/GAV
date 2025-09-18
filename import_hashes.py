import sqlite3
from datetime import datetime, timezone

DB_FILES = {
    "SHA256": "signatures_sha256.db",
    "SHA1": "signatures_sha1.db",
    "MD5": "signatures_md5.db"
}

TXT_FILES = {
    "SHA256": "hashes_sha256.txt",
    "SHA1": "hashes_sha1.txt",
    "MD5": "hashes_md5.txt"
}

def create_table(conn):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS signatures (
        hash TEXT PRIMARY KEY,
        added_at TEXT
    );
    """)
    conn.commit()

def import_hashes(txt_path, db_path):
    conn = sqlite3.connect(db_path)
    create_table(conn)
    cur = conn.cursor()
    added = 0
    skipped = 0
    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            h = line.strip().lower()
            if not h:
                continue
            try:
                cur.execute("INSERT INTO signatures(hash, added_at) VALUES (?, ?)",
                            (h, datetime.now(timezone.utc).isoformat()))
                added += 1
            except sqlite3.IntegrityError:
                skipped += 1
    conn.commit()
    conn.close()
    return added, skipped

if __name__ == "__main__":
    total_added = 0
    total_skipped = 0
    for algo in ["SHA256", "SHA1", "MD5"]:
        added, skipped = import_hashes(TXT_FILES[algo], DB_FILES[algo])
        print(f"{algo} -> New:{added}, Skipped:{skipped}")
        total_added += added
        total_skipped += skipped
    print(f"Toplam -> New:{total_added}, Skipped:{total_skipped}")
