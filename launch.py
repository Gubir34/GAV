import subprocess
import platform
import os
import urllib.request
import curses
from lang_loader import LangLoader

INPUT_FILE = "hashes_raw.txt"
HASHES_URL = "https://github.com/Gubir34/GAV/releases/download/antivirus/hashes_raw.txt"

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

def run_recompile(lang):
    print(lang.t("recompile_start"))
    subprocess.run(["python3" if platform.system() != "Windows" else "py", "recompile.py"], check=True)
    print(lang.t("recompile_done"))

def run_import_hashes(lang):
    print(lang.t("import_hashes_start"))
    subprocess.run(["python3" if platform.system() != "Windows" else "py", "import_hashes.py"], check=True)
    print(lang.t("import_hashes_done"))

def start_scan(lang):
    folder = input(lang.t("scan_prompt") + ": ")
    subprocess.run(["python3" if platform.system() != "Windows" else "py", "scan_folder.py", folder], check=True)

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

    print(lang.t("loading_hashes"))
    run_recompile(lang)
    run_import_hashes(lang)
    start_scan(lang)
    print(lang.t("scan_done"))

if __name__ == "__main__":
    main()

