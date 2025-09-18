
import subprocess
import sys
import pathlib

REQUIRED_PACKAGES = ["tqdm"]

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", package])

def check_and_install_packages():
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg)
        except ImportError:
            print(f"[!] Package is missing: {pkg}. Downloading and Installing...")
            install_package(pkg)

def run_script(script_name):
    print(f"\n[+] Executing: {script_name}")
    result = subprocess.run([sys.executable, script_name])
    if result.returncode != 0:
        print(f"[!] Error: {script_name} failed!")
        sys.exit(1)

def ask_directories():
    dirs = input("\nEnter the directory that you want to scan (for example C: for the main drive and / for everything): ").strip()
    if dirs == "/":
        drives = [f"{d}:\\" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if pathlib.Path(f"{d}:\\").exists()]
        return drives
    else:
        return [dirs]

def scan_folder_with_progress(folder):
    print(f"\n[+] Scan Initating: {folder}")
    result = subprocess.run([sys.executable, "scan_folder.py", folder])
    if result.returncode != 0:
        print(f"[!] An error ocurred during the scan: {folder}")

if __name__ == "__main__":
    check_and_install_packages()

    run_script("recompile.py")

    run_script("import_hashes.py")

    folders_to_scan = ask_directories()
    for folder in folders_to_scan:
        scan_folder_with_progress(folder)

    print("\n[+] All Operations completed!")
