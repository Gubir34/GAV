import subprocess
import os
import sys
import urllib.request
import curses
import gav_core
from lang_loader import LangLoader

# Every helper script and data file is resolved next to this file, never from the current directory.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, "hashes_raw.txt")
HASHES_URL = "https://www.dropbox.com/scl/fi/vh12opwwnigvl9f0v9fqp/hashes_raw.txt?rlkey=bwzdy2shcjjfoqeias1hb2mzc&st=t7n3hktp&dl=1"

supported_langs = [
    ("English", "en"),
    ("Türkçe", "tr"),
    ("Español", "es"),
    ("Français", "fr"),
    ("Deutsch", "de"),
    ("Italiano", "it"),
    ("Português", "pt"),
    ("Русский", "ru"),
    ("日本語", "ja"),
    ("한국어", "ko")
]

# Dil seçimi TUI
def select_language(stdscr):
    curses.curs_set(0)
    current_row = 0

    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "Select language / Dil seçin / Выберите язык:")
        for idx, (name, code) in enumerate(supported_langs):
            if idx == current_row:
                stdscr.addstr(idx + 2, 2, f"> {name}", curses.A_REVERSE)
            else:
                stdscr.addstr(idx + 2, 2, f"  {name}")
        key = stdscr.getch()
        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(supported_langs) - 1:
            current_row += 1
        elif key in [10, 13]:  # Enter
            return supported_langs[current_row][1]

def run_script(name, *args):
    subprocess.run([sys.executable, os.path.join(BASE_DIR, name), *args], cwd=BASE_DIR, check=True)


def ensure_engine():
    try:
        gav_core.find_engine()
    except gav_core.EngineNotFoundError:
        print("[!] GavCore engine not found, installing...")
        run_script("install_gavcore.py")


def run_recompile(lang):
    print(lang.t("recompile_start"))
    run_script("recompile.py")
    print(lang.t("recompile_done"))


def run_import_hashes(lang):
    print(lang.t("import_hashes_start"))
    run_script("import_hashes.py")
    print(lang.t("import_hashes_done"))


def start_scan(lang):
    folder = input(lang.t("scan_prompt") + ": ")
    run_script("scan_folder.py", folder)


def main():
    # Dil seçimi
    selected_lang_code = curses.wrapper(select_language)
    lang = LangLoader("lng.ltf", default=selected_lang_code)

    print(lang.t("launching"))

    # Hash dosyasını kontrol et ve indir
    if not os.path.exists(INPUT_FILE):
        print("[!] hashes_raw.txt not found, downloading...")
        urllib.request.urlretrieve(HASHES_URL, INPUT_FILE)
        print("[+] Download completed: hashes_raw.txt")

    ensure_engine()
    print(lang.t("loading_hashes"))
    run_recompile(lang)
    run_import_hashes(lang)
    start_scan(lang)
    print(lang.t("scan_done"))

if __name__ == "__main__":
    main()





