import os
import hashlib
import sys
from tqdm import tqdm

def load_hashes(filename):
    if not os.path.exists(filename):
        return set()
    with open(filename, "r") as f:
        return set(h.strip() for h in f)

SHA256_HASHES = load_hashes("hashes_sha256.txt")
SHA1_HASHES = load_hashes("hashes_sha1.txt")
MD5_HASHES = load_hashes("hashes_md5.txt")

def hash_file(path):
    sha256 = hashlib.sha256()
    sha1 = hashlib.sha1()
    md5 = hashlib.md5()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
                sha1.update(chunk)
                md5.update(chunk)
        return sha256.hexdigest(), sha1.hexdigest(), md5.hexdigest()
    except:
        return None, None, None

def scan_folder(folder):
    all_files = []
    for root, dirs, files in os.walk(folder):
        for file in files:
            all_files.append(os.path.join(root, file))
    for file in tqdm(all_files, desc="Scanning files"):
        s256, s1, m5 = hash_file(file)
        if s256 in SHA256_HASHES or s1 in SHA1_HASHES or m5 in MD5_HASHES:
            print(f"[!] Threat detected: {file} -> {s256[:16]}...")

if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    scan_folder(folder)
