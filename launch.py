import subprocess
import platform
import os
import urllib.request
from lang_loader import LangLoader

lang = LangLoader("lng.ltf", default="en")

INPUT_FILE = "hashes_raw.txt"

HASHES_URL = "https://edef1.pcloud.com/cBZwzHz1OZUoETr27ZZZGhYy0kZ2ZZSa0ZkZu7cILZ9zZhHZV8ZV0ZhpZMXZvLZK4ZKRZkpZwFZckZIkZNzZ5kyUZTBettr1UrquDWYYw6lsirFgXUSJV/hashes_raw.txt"


def run_recompile():
    print(lang.t("recompile_start"))
    subprocess.run(["python3" if platform.system() != "Windows" else "py", "recompile.py"], check=True)
    print(lang.t("recompile_done"))

if not os.path.exists(INPUT_FILE):
    print("[!] hashes_raw.txt not found, downloading...")
    urllib.request.urlretrieve(HASHES_URL, INPUT_FILE)
    print("[+] Download completed: hashes_raw.txt")

def run_import_hashes():
    print(lang.t("import_hashes_start"))
    subprocess.run(["python3" if platform.system() != "Windows" else "py", "import_hashes.py"], check=True)
    print(lang.t("import_hashes_done"))

def start_scan():
    folder = input(lang.t("scan_prompt") + ": ")
    subprocess.run(["python3" if platform.system() != "Windows" else "py", "scan_folder.py", folder], check=True)

def main():
    print(lang.t("launching"))
    print(lang.t("loading_hashes"))
    run_recompile()
    run_import_hashes()
    start_scan()
    print(lang.t("scan_done"))

if __name__ == "__main__":
    main()

