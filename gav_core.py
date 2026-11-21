"""Python client for the GavCore scan engine (https://github.com/Gubir34/GavCore, C++).

The engine runs as a separate process and streams JSON events; this module turns them
into callbacks for the CLI and GTK front-ends.

    python gav_core.py <folder>    run the engine with human readable output
"""
import json
import os
import subprocess
import sys
import threading
from dataclasses import dataclass, field

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_EXE = "gavcore.exe" if os.name == "nt" else "gavcore"


class NoSignaturesError(RuntimeError):
    """The engine found no signature database (it refuses to fail open)."""


class EngineNotFoundError(RuntimeError):
    """The gavcore executable could not be located."""


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
    """Escape control/format characters so file names cannot inject terminal sequences or bidi tricks."""
    return "".join(c if c.isprintable() else f"\\x{ord(c):02x}" for c in str(text))


def _install_dirs():
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
        return [os.path.join(local, "Programs", "GavCore")]
    return [os.path.join(os.path.expanduser("~"), ".local", "bin"), "/usr/local/bin"]


def find_engine():
    """Locate gavcore: $GAVCORE, PATH, then the folders install_gavcore.py uses. Never the CWD."""
    override = os.environ.get("GAVCORE")
    if override:
        if os.path.isfile(override):
            return override
        raise EngineNotFoundError(f"GAVCORE points to a missing file: {override}")
    # Manual PATH walk: shutil.which() on Windows also looks in the current directory.
    path_dirs = [d for d in os.environ.get("PATH", "").split(os.pathsep) if d and os.path.isabs(d)]
    for directory in path_dirs + _install_dirs():
        path = os.path.join(directory, _EXE)
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    raise EngineNotFoundError("gavcore is not installed. Run: python install_gavcore.py")


def _engine_command(root, json_mode, db_dir, threads, engine):
    cmd = [engine or find_engine(), "--db-dir", db_dir or BASE_DIR]
    if threads:
        cmd += ["--threads", str(threads)]
    if json_mode:
        cmd.append("--json")
    return cmd + ["--", root]  # "--": a path starting with "-" is never read as an option


def scan(root, on_start=None, on_progress=None, on_threat=None, on_error=None, cancel_event=None,
         db_dir=None, threads=0, engine=None):
    """Run a scan with GavCore. Callbacks run on the calling thread."""
    cmd = _engine_command(root, True, db_dir, threads, engine)
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                            text=True, encoding="utf-8", errors="replace", creationflags=flags)

    finished = threading.Event()
    if cancel_event is not None:
        def watch():
            while not finished.is_set():
                if cancel_event.wait(0.1):
                    if proc.poll() is None:
                        proc.terminate()  # SIGTERM -> engine stops and still reports "done"
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            proc.kill()  # never leave the GUI waiting on a stuck engine
                    return
        threading.Thread(target=watch, daemon=True).start()

    stderr_lines = []
    stderr_reader = threading.Thread(target=lambda: stderr_lines.extend(proc.stderr), daemon=True)
    stderr_reader.start()

    summary, done, fatal = ScanSummary(), False, None
    try:
        for line in proc.stdout:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            kind = ev.get("type")
            if kind == "start":
                summary.total = ev["total"]
                if on_start:
                    on_start(summary.total)
            elif kind == "progress":
                if on_progress:
                    on_progress(ev["done"], ev["total"])
            elif kind == "threat":
                threat = Threat(ev["path"], ev["algo"], ev["hash"])
                summary.threats.append(threat)
                if on_threat:
                    on_threat(threat)
            elif kind == "error":
                err = ScanError(ev["path"], ev["reason"])
                summary.errors.append(err)
                if on_error:
                    on_error(err)
            elif kind == "done":
                done = True
                summary.total = ev["total"]
                summary.scanned = ev["scanned"]
                summary.skipped = ev["skipped"]
                summary.cancelled = ev.get("cancelled", False)
                summary.elapsed = ev["elapsed"]
            elif kind == "fatal":
                fatal = ev.get("message", "")
    finally:
        proc.wait()
        finished.set()
        stderr_reader.join(timeout=1)

    if fatal is not None:
        if proc.returncode == 2:
            raise NoSignaturesError(fatal)
        raise RuntimeError(fatal)
    if not done:
        if cancel_event is not None and cancel_event.is_set():
            summary.cancelled = True
        else:
            raise RuntimeError("".join(stderr_lines).strip() or f"gavcore exited with code {proc.returncode}")
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


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        print("usage: gav_core.py <folder>", file=sys.stderr)
        sys.exit(64)
    try:
        sys.exit(subprocess.call(_engine_command(args[0], False, None, 0, None)))
    except EngineNotFoundError as e:
        print(f"[x] {e}", file=sys.stderr)
        sys.exit(69)
