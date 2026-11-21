"""Download GavCore from its GitHub release and install it as the `gavcore` command.

    python install_gavcore.py              install the version pinned in gavcore.lock.json
    python install_gavcore.py --system     install to /usr/local/bin (Linux/macOS, needs root)
    python install_gavcore.py --dir DIR    install somewhere else
    python install_gavcore.py --latest     newest release (checked only against its own SHA256SUMS)
    python install_gavcore.py --check      show what is installed
    python install_gavcore.py --uninstall

The pinned version's SHA256 hashes live in gavcore.lock.json, so a tampered download is
rejected before anything is written to the install folder.
"""
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCK_FILE = os.path.join(BASE_DIR, "gavcore.lock.json")
REPO = "Gubir34/GavCore"
MAX_DOWNLOAD = 64 * 1024 * 1024
IS_WINDOWS = os.name == "nt"
EXE = "gavcore.exe" if IS_WINDOWS else "gavcore"


class InstallError(RuntimeError):
    pass


class IntegrityError(InstallError):
    pass


def asset_name(system=None, machine=None):
    system = (system or platform.system()).lower()
    machine = (machine or platform.machine()).lower()
    arch = {"x86_64": "x86_64", "amd64": "x86_64", "aarch64": "arm64", "arm64": "arm64"}.get(machine)
    if system == "linux" and arch:
        return f"gavcore-linux-{arch}"
    if system == "darwin" and arch == "arm64":
        return "gavcore-macos-arm64"
    if system == "windows" and arch:
        return "gavcore-windows-x64.exe"  # Windows on ARM runs it through x64 emulation
    raise InstallError(f"No pre-built GavCore for {system}/{machine}; build it from https://github.com/{REPO}")


def default_install_dir(system_wide=False):
    if IS_WINDOWS:
        return os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")),
                            "Programs", "GavCore")
    if system_wide or (hasattr(os, "geteuid") and os.geteuid() == 0):
        return "/usr/local/bin"
    return os.path.join(os.path.expanduser("~"), ".local", "bin")


def load_lock(path=LOCK_FILE):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def download(url, limit=MAX_DOWNLOAD):
    request = urllib.request.Request(url, headers={"User-Agent": "gav-installer"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise InstallError(f"Download too large: {url}")
    return data


def parse_sha256sums(text):
    sums = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2:
            sums[parts[1].lstrip("*")] = parts[0].lower()
    return sums


def resolve_release(lock, latest=False):
    """Returns (version, base_url, {asset: sha256})."""
    if not latest:
        return lock["version"], lock["base_url"].format(version=lock["version"]), lock["assets"]
    info = json.loads(download(f"https://api.github.com/repos/{REPO}/releases/latest"))
    version = info["tag_name"].lstrip("v")
    base_url = f"https://github.com/{REPO}/releases/download/{info['tag_name']}/"
    print("[!] --latest: the binary is only checked against the release's own SHA256SUMS", file=sys.stderr)
    return version, base_url, parse_sha256sums(download(base_url + "SHA256SUMS").decode())


def fetch_verified(base_url, asset, expected):
    if not expected:
        raise InstallError(f"No pinned SHA256 for {asset} in gavcore.lock.json")
    data = download(base_url + asset)
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected.lower():
        raise IntegrityError(f"SHA256 mismatch for {asset}: expected {expected}, got {actual}")
    return data


def write_executable(data, dest_dir):
    """Atomically places the binary at dest_dir/gavcore[.exe]."""
    os.makedirs(dest_dir, exist_ok=True)
    target = os.path.join(dest_dir, EXE)
    fd, tmp = tempfile.mkstemp(prefix=".gavcore-", dir=dest_dir)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.chmod(tmp, 0o755)
        os.replace(tmp, target)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return target


def engine_version(path):
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=15)
    except OSError:
        return None
    parts = out.stdout.split()
    return parts[1] if out.returncode == 0 and len(parts) == 2 else None


def _norm(path):
    return os.path.normcase(os.path.normpath(os.path.expandvars(path)))


def on_path(directory):
    return any(_norm(p) == _norm(directory) for p in os.environ.get("PATH", "").split(os.pathsep) if p)


def find_installed(dest_dir):
    """PATH (absolute entries only; never the current directory), then dest_dir."""
    dirs = [d for d in os.environ.get("PATH", "").split(os.pathsep) if d and os.path.isabs(d)] + [dest_dir]
    for directory in dirs:
        path = os.path.join(directory, EXE)
        if os.path.isfile(path):
            return path
    return None


def _windows_user_path(directory, add):
    import ctypes
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
        try:
            value, kind = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            value, kind = "", winreg.REG_EXPAND_SZ
        parts = [p for p in value.split(";") if p]
        present = [p for p in parts if _norm(p) == _norm(directory)]
        if add and not present:
            parts.append(directory)
        elif not add and present:
            parts = [p for p in parts if p not in present]
        else:
            return False
        winreg.SetValueEx(key, "Path", 0, kind, ";".join(parts))
    HWND_BROADCAST, WM_SETTINGCHANGE, SMTO_ABORTIFHUNG = 0xFFFF, 0x1A, 0x2
    ctypes.windll.user32.SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment",
                                             SMTO_ABORTIFHUNG, 5000, None)
    return True


def install(dest_dir, latest=False, lock=None, asset=None):
    lock = lock or load_lock()
    asset = asset or asset_name()
    version, base_url, hashes = resolve_release(lock, latest)
    print(f"[*] Downloading GavCore {version} ({asset})")
    data = fetch_verified(base_url, asset, hashes.get(asset))
    target = write_executable(data, dest_dir)
    print(f"[+] Installed {target} (sha256 verified)")
    return target


def uninstall(dest_dir):
    target = os.path.join(dest_dir, EXE)
    if os.path.exists(target):
        os.unlink(target)
        print(f"[+] Removed {target}")
    else:
        print(f"[-] Not installed in {dest_dir}")
    if IS_WINDOWS and _windows_user_path(dest_dir, add=False):
        print(f"[+] Removed {dest_dir} from your PATH")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Install the GavCore engine as the `gavcore` command.")
    parser.add_argument("--dir", help="install folder")
    parser.add_argument("--system", action="store_true", help="install to /usr/local/bin (Linux/macOS)")
    parser.add_argument("--latest", action="store_true", help="install the newest release instead of the pinned one")
    parser.add_argument("--check", action="store_true", help="show the installed engine")
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args(argv)
    dest_dir = os.path.abspath(args.dir) if args.dir else default_install_dir(args.system)

    try:
        if args.uninstall:
            uninstall(dest_dir)
            return 0
        if args.check:
            found = find_installed(dest_dir)
            if not found:
                print("[-] gavcore is not installed")
                return 1
            print(f"[+] {found}: gavcore {engine_version(found) or '?'} (pinned: {load_lock()['version']})")
            return 0

        target = install(dest_dir, latest=args.latest)
        version = engine_version(target)
        if not version:
            raise InstallError(f"{target} does not run on this system")
        print(f"[+] gavcore {version} works")
        if IS_WINDOWS:
            if _windows_user_path(dest_dir, add=True):
                print(f"[+] Added {dest_dir} to your PATH (open a new terminal to use `gavcore`)")
        elif not on_path(dest_dir):
            print(f"[!] {dest_dir} is not on your PATH. Add this to your shell profile:\n"
                  f'    export PATH="{dest_dir}:$PATH"')
        return 0
    except PermissionError as e:
        print(f"[x] {e}. Try again with sudo, or without --system.", file=sys.stderr)
    except (InstallError, OSError, ValueError, KeyError) as e:
        print(f"[x] {e}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
