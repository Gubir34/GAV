"""GAV scan engine shared by the CLI, GTK and WinUI front-ends.

Usage as a CLI:
    python gav_core.py <folder>           human readable output
    python gav_core.py --json <folder>    one JSON object per line (used by the WinUI app)
"""
import hashlib
import json
import os
import sqlite3
import stat
import sys
import threading
import time
from dataclasses import dataclass, field

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_FILES = {
    "SHA256": "signatures_sha256.db",
    "SHA1": "signatures_sha1.db",
    "MD5": "signatures_md5.db",
}

CHUNK_SIZE = 1024 * 1024
_OPEN_FLAGS = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)


class NoSignaturesError(RuntimeError):
    """Raised when no signature database could be loaded (refuse to fail open)."""


@dataclass
class Threat:
    path: str
    algo: str
    hash: str


@dataclass
class ScanError:
    path: str
    reason: str


@dataclass
class ScanSummary:
    total: int = 0
    scanned: int = 0
    skipped: int = 0
    threats: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    cancelled: bool = False
    elapsed: float = 0.0


def safe_display(text):
    """Escape control characters so file names cannot inject terminal sequences."""
    return "".join(c if c.isprintable() else f"\\x{ord(c):02x}" for c in str(text))


def load_signatures(db_dir=BASE_DIR):
    signatures = {algo: set() for algo in DB_FILES}
    for algo, name in DB_FILES.items():
        path = os.path.join(db_dir, name)
        if not os.path.exists(path):
            continue
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            signatures[algo].update(row[0].lower() for row in conn.execute("SELECT hash FROM signatures"))
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()
    if not any(signatures.values()):
        raise NoSignaturesError("No signatures loaded; run recompile.py and import_hashes.py first")
    return signatures


def hash_file(path):
    """Hash a regular file in chunks. Returns {algo: hexdigest} or raises OSError/ValueError."""
    fd = os.open(path, _OPEN_FLAGS)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("not a regular file")
        if hasattr(os, "O_NONBLOCK") and os.O_NONBLOCK:
            os.set_blocking(fd, True)
        hashers = {"SHA256": hashlib.sha256(), "SHA1": hashlib.sha1(), "MD5": hashlib.md5()}
        while True:
            chunk = os.read(fd, CHUNK_SIZE)
            if not chunk:
                break
            for h in hashers.values():
                h.update(chunk)
        return {algo: h.hexdigest() for algo, h in hashers.items()}
    finally:
        os.close(fd)


def collect_files(root, on_error=None):
    """Walk root without following symlinks; report unreadable directories instead of hiding them."""
    files, skipped = [], 0

    def walk_error(err):
        if on_error:
            on_error(ScanError(err.filename or root, err.strerror or str(err)))

    for dirpath, _dirs, names in os.walk(root, onerror=walk_error, followlinks=False):
        for name in names:
            path = os.path.join(dirpath, name)
            try:
                mode = os.lstat(path).st_mode
            except OSError as e:
                if on_error:
                    on_error(ScanError(path, e.strerror or str(e)))
                continue
            if stat.S_ISREG(mode):
                files.append(path)
            else:
                skipped += 1  # symlinks, FIFOs, sockets, devices
    return files, skipped


def scan(root, signatures=None, on_start=None, on_progress=None, on_threat=None, on_error=None,
         cancel_event=None):
    """Scan a folder. Callbacks are invoked from the calling thread."""
    started = time.monotonic()
    if signatures is None:
        signatures = load_signatures()
    summary = ScanSummary()

    def record_error(err):
        summary.errors.append(err)
        if on_error:
            on_error(err)

    if os.path.isfile(root) and not os.path.islink(root):
        files, summary.skipped = [root], 0
    else:
        files, summary.skipped = collect_files(root, record_error)
    summary.total = len(files)
    if on_start:
        on_start(summary.total)

    for index, path in enumerate(files, 1):
        if cancel_event is not None and cancel_event.is_set():
            summary.cancelled = True
            break
        try:
            digests = hash_file(path)
        except (OSError, ValueError) as e:
            record_error(ScanError(path, getattr(e, "strerror", None) or str(e)))
        else:
            summary.scanned += 1
            for algo, digest in digests.items():
                if digest in signatures.get(algo, ()):
                    threat = Threat(path, algo, digest)
                    summary.threats.append(threat)
                    if on_threat:
                        on_threat(threat)
                    break
        if on_progress:
            on_progress(index, summary.total, path)

    summary.elapsed = time.monotonic() - started
    return summary


class ScanWorker(threading.Thread):
    """Runs a scan in the background; GUIs pass thread-safe callbacks."""

    def __init__(self, root, **callbacks):
        super().__init__(daemon=True)
        self.root = root
        self.callbacks = callbacks
        self.cancel_event = threading.Event()
        self.summary = None
        self.exception = None

    def cancel(self):
        self.cancel_event.set()

    def run(self):
        on_done = self.callbacks.pop("on_done", None)
        try:
            self.summary = scan(self.root, cancel_event=self.cancel_event, **self.callbacks)
        except Exception as e:  # surfaced to the GUI instead of dying silently
            self.exception = e
        if on_done:
            on_done(self.summary, self.exception)


def _main_json(root):
    def emit(obj):
        sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    last = [0.0]

    def progress(done, total, path):
        now = time.monotonic()
        if done == total or now - last[0] >= 0.1:
            last[0] = now
            emit({"type": "progress", "done": done, "total": total, "path": path})

    try:
        summary = scan(
            root,
            on_start=lambda total: emit({"type": "start", "total": total}),
            on_progress=progress,
            on_threat=lambda t: emit({"type": "threat", "path": t.path, "algo": t.algo, "hash": t.hash}),
            on_error=lambda e: emit({"type": "error", "path": e.path, "reason": e.reason}),
        )
    except NoSignaturesError as e:
        emit({"type": "fatal", "message": str(e)})
        return 2
    emit({"type": "done", "total": summary.total, "scanned": summary.scanned, "skipped": summary.skipped,
          "threats": len(summary.threats), "errors": len(summary.errors), "elapsed": round(summary.elapsed, 3)})
    return 1 if summary.threats else 0


def _main_text(root):
    try:
        summary = scan(
            root,
            on_threat=lambda t: print(f"[!] Threat: {safe_display(t.path)} -> {t.algo} {t.hash}"),
            on_error=lambda e: print(f"[?] Not scanned: {safe_display(e.path)} ({e.reason})"),
        )
    except NoSignaturesError as e:
        print(f"[x] {e}")
        return 2
    print(f"Scanned {summary.scanned}/{summary.total}, skipped {summary.skipped}, "
          f"threats {len(summary.threats)}, errors {len(summary.errors)} in {summary.elapsed:.1f}s")
    return 1 if summary.threats else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    as_json = "--json" in args
    args = [a for a in args if a != "--json"]
    if len(args) != 1 or not os.path.exists(args[0]):
        print("usage: gav_core.py [--json] <folder>", file=sys.stderr)
        sys.exit(64)
    sys.exit(_main_json(args[0]) if as_json else _main_text(args[0]))
