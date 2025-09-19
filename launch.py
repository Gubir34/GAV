import os
import platform
import subprocess
from tqdm import tqdm

def run_recompile():
    print("[*] Recompiling hashes...")
    subprocess.run(["python3" if platform.system() != "Windows" else "py", "recompile.py"], check=True)

def run_import_hashes():
    print("[*] Importing hashes into database...")
    subprocess.run(["python3" if platform.system() != "Windows" else "py", "import_hashes.py"], check=True)

def run_scan():
    print("[*] Starting scan...")
    folder = input("Enter folder or drive to scan (e.g., C:\\ or /): ").strip()
    subprocess.run(["python3" if platform.system() != "Windows" else "py", "scan_folder.py", folder], check=True)

def main():
    print("=== GAV Antivirus Launcher ===")
    run_recompile()
    run_import_hashes()
    run_scan()
    print("[*] Scan completed.")

if __name__ == "__main__":
    main()
