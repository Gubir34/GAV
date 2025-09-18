import re

INPUT_FILE = "hashes_raw.txt"

SHA256_FILE = "hashes_sha256.txt"
SHA1_FILE   = "hashes_sha1.txt"
MD5_FILE    = "hashes_md5.txt"

sha256_re = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
sha1_re   = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
md5_re    = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)

hash_sets = {
    "SHA256": set(),
    "SHA1": set(),
    "MD5": set()
}

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    for line in f:
        h = line.strip().lower()
        if not h:
            continue
        if sha256_re.match(h):
            hash_sets["SHA256"].add(h)
        elif sha1_re.match(h):
            hash_sets["SHA1"].add(h)
        elif md5_re.match(h):
            hash_sets["MD5"].add(h)

# txt olarak kaydet
with open(SHA256_FILE, "w", encoding="utf-8", newline="\n") as f:
    f.writelines(f"{h}\n" for h in hash_sets["SHA256"])
with open(SHA1_FILE, "w", encoding="utf-8", newline="\n") as f:
    f.writelines(f"{h}\n" for h in hash_sets["SHA1"])
with open(MD5_FILE, "w", encoding="utf-8", newline="\n") as f:
    f.writelines(f"{h}\n" for h in hash_sets["MD5"])

print(f"Tamamlandı. SHA256:{len(hash_sets['SHA256'])}, SHA1:{len(hash_sets['SHA1'])}, MD5:{len(hash_sets['MD5'])}")
