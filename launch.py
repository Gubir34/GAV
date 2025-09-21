import os
import subprocess
import platform
import urllib.request
from lang_loader import get_text

HASHES_URL = "https://edef1.pcloud.com/cBZwzHz1OZUoETr27ZZZGhYy0kZ2ZZSa0ZkZu7cILZ9zZhHZV8ZV0ZhpZMXZvLZK4ZKRZkpZwFZckZIkZNzZ5kyUZTBettr1UrquDWYYw6lsirFgXUSJV/hashes_raw.txt"
HASHES_FILE = "hashes_raw.txt"

def download_hashes():
    print(get_text("loading_hashes"))
    urllib.request.urlretrieve(HASHES_URL, HASHES_FILE)
    print(get_text("downloaded_hashes"))

def run_recompile():
    if not os.path.exists(HASHES_FILE):
        download_hashes()
    subprocess.run(["python3" if platform.system() != "Windows" else "py", "recompile.py"], check=True)

def run_scan():
    folder = input(get_text("scan_prompt"))
    subprocess.run(["python3" if platform.system() != "Windows" else "py", "scan_folder.py", folder], check=True)

def main():
    print(get_text("launching"))
    run_recompile()
    run_scan()

if __name__ == "__main__":
    main()
