import os
import hashlib
from lang_loader import LangLoader
from tqdm import tqdm

lang = LangLoader("lng.ltf", default="en")

def compute_hashes(file_path):
    # Burada sadece örnek hash hesaplama
    with open(file_path, "rb") as f:
        data = f.read()
    return hashlib.sha256(data).hexdigest()

def scan_folder(folder):
    all_files = []
    for root, dirs, files in os.walk(folder):
        for f in files:
            all_files.append(os.path.join(root, f))

    for i, file in enumerate(tqdm(all_files, desc=lang.t("scan_progress", progress=0))):
        h = compute_hashes(file)
        # örnek: hash kontrolü
        # if h in virus_db:
        #     print(lang.t("threat_detected", file=file, hash=h))
        progress = int((i+1)/len(all_files)*100)
        tqdm.write(lang.t("scan_progress", progress=progress))

if __name__ == "__main__":
    import sys
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    scan_folder(folder)
