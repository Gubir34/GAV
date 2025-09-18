# launch.py (otomatik paket yükleme ve ilerleme destekli)

import subprocess
import sys
import pathlib

REQUIRED_PACKAGES = ["tqdm"]

def install_package(package):
    """Eksik paketleri yükler"""
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", package])

def check_and_install_packages():
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg)
        except ImportError:
            print(f"[!] Paket eksik: {pkg}. Yükleniyor...")
            install_package(pkg)

def run_script(script_name):
    print(f"\n[+] Çalıştırılıyor: {script_name}")
    result = subprocess.run([sys.executable, script_name])
    if result.returncode != 0:
        print(f"[!] Hata: {script_name} başarısız oldu!")
        sys.exit(1)

def ask_directories():
    dirs = input("\nTarayacağınız dizinleri girin (örn. C: veya / tüm sürücüler): ").strip()
    if dirs == "/":
        # Windows: tüm sürücüler
        drives = [f"{d}:\\" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if pathlib.Path(f"{d}:\\").exists()]
        return drives
    else:
        return [dirs]

def scan_folder_with_progress(folder):
    print(f"\n[+] Tarama başlıyor: {folder}")
    result = subprocess.run([sys.executable, "scan_folder.py", folder])
    if result.returncode != 0:
        print(f"[!] Tarama sırasında hata oluştu: {folder}")

if __name__ == "__main__":
    # 0️⃣ Paketleri kontrol et ve yükle
    check_and_install_packages()

    # 1️⃣ recompile.py
    run_script("recompile.py")

    # 2️⃣ import_hashes.py
    run_script("import_hashes.py")

    # 3️⃣ scan_folder.py
    folders_to_scan = ask_directories()
    for folder in folders_to_scan:
        scan_folder_with_progress(folder)

    print("\n[+] Tüm işlemler tamamlandı!")
