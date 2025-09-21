import subprocess
import platform
from lang_loader import LangLoader

lang = LangLoader("lng.ltf", default="en")

def run_recompile():
    print(lang.t("recompile_start"))
    subprocess.run(["python3" if platform.system() != "Windows" else "py", "recompile.py"], check=True)
    print(lang.t("recompile_done"))

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
