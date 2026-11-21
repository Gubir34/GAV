"""End-to-end tests of the GavCore engine through the Python client."""
import hashlib
import os
import sqlite3
import sys
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gav_core  # noqa: E402

try:
    ENGINE = gav_core.find_engine()
except gav_core.EngineNotFoundError:
    if os.environ.get("GAV_REQUIRE_ENGINE") == "1":  # CI: a missing engine must fail, not skip
        raise
    ENGINE = None
pytestmark = pytest.mark.skipif(ENGINE is None, reason="gavcore is not installed (python install_gavcore.py)")

SAMPLES = {"SHA256": b"GAV-TEST-ONE", "SHA1": b"GAV-TEST-TWO", "MD5": b"GAV-TEST-THREE"}
DB_NAMES = {"SHA256": "signatures_sha256.db", "SHA1": "signatures_sha1.db", "MD5": "signatures_md5.db"}


def make_db(db_dir, hashes):
    """hashes: {algo: [hexdigest, ...]}"""
    db_dir.mkdir(exist_ok=True)
    for algo, values in hashes.items():
        conn = sqlite3.connect(db_dir / DB_NAMES[algo])
        conn.execute("CREATE TABLE IF NOT EXISTS signatures (hash TEXT PRIMARY KEY, added_at TEXT)")
        conn.executemany("INSERT OR IGNORE INTO signatures VALUES (?, '')", [(v,) for v in values])
        conn.commit()
        conn.close()
    return str(db_dir)


@pytest.fixture
def db(tmp_path):
    return make_db(tmp_path / "db", {a: [hashlib.new(a.lower(), d).hexdigest()] for a, d in SAMPLES.items()})


@pytest.fixture
def target(tmp_path):
    path = tmp_path / "scan"
    path.mkdir()
    return path


def run(target, db, **kw):
    return gav_core.scan(str(target), db_dir=db, **kw)


def test_detects_all_three_algorithms(target, db):
    for algo, data in SAMPLES.items():
        (target / f"{algo}.bin").write_bytes(data)
    (target / "clean.txt").write_bytes(b"clean")
    summary = run(target, db)
    assert sorted(t.algo for t in summary.threats) == ["MD5", "SHA1", "SHA256"]
    assert summary.scanned == 4 and summary.total == 4


@pytest.mark.parametrize("size", [0, 1, 1024 * 1024 - 1, 1024 * 1024, 3 * 1024 * 1024 + 7])
def test_digests_match_hashlib_across_chunk_boundaries(tmp_path, target, size):
    data = bytes(range(256)) * (size // 256) + bytes(range(size % 256))
    (target / "f.bin").write_bytes(data)
    for algo in SAMPLES:
        db = make_db(tmp_path / f"db_{algo}", {algo: [hashlib.new(algo.lower(), data).hexdigest()]})
        threats = run(target, db).threats
        assert [(t.algo, t.hash) for t in threats] == [(algo, hashlib.new(algo.lower(), data).hexdigest())]


def test_uppercase_signatures_are_accepted(tmp_path, target):
    db = make_db(tmp_path / "db", {"SHA256": [hashlib.sha256(b"x").hexdigest().upper()]})
    (target / "x").write_bytes(b"x")
    assert len(run(target, db).threats) == 1


def test_many_files_with_threads(target, db):
    for i in range(500):
        (target / f"f{i}").write_bytes(str(i).encode())
    (target / "mal").write_bytes(SAMPLES["SHA1"])
    progress = []
    summary = run(target, db, threads=4, on_progress=lambda d, t: progress.append(d))
    assert summary.scanned == 501 and len(summary.threats) == 1
    assert progress[-1] == 501 and progress == sorted(progress)


def test_non_ascii_file_names(target, db):
    (target / "çğıöşü_日本.exe").write_bytes(SAMPLES["SHA256"])
    assert os.path.basename(run(target, db).threats[0].path) == "çğıöşü_日本.exe"


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX only")
def test_fifo_and_symlinks_are_skipped(target, db):
    os.mkfifo(target / "pipe")
    os.symlink("/dev/zero", target / "zero")
    os.symlink(target, target / "loop")
    (target / "mal").write_bytes(SAMPLES["SHA256"])
    summary = run(target, db)
    assert summary.skipped == 3 and len(summary.threats) == 1


@pytest.mark.skipif(not hasattr(os, "geteuid") or os.geteuid() == 0, reason="needs a non-root POSIX user")
def test_unreadable_entries_are_reported(target, db):
    locked_file = target / "locked.bin"
    locked_file.write_bytes(SAMPLES["SHA256"])
    locked_file.chmod(0)
    locked_dir = target / "locked_dir"
    locked_dir.mkdir()
    locked_dir.chmod(0)
    try:
        summary = run(target, db)
    finally:
        locked_file.chmod(0o600)
        locked_dir.chmod(0o700)
    assert {os.path.basename(e.path) for e in summary.errors} == {"locked.bin", "locked_dir"}


def test_missing_database_refuses_to_scan(tmp_path, target):
    (tmp_path / "empty").mkdir()
    with pytest.raises(gav_core.NoSignaturesError):
        run(target, str(tmp_path / "empty"))


def test_dash_prefixed_target(tmp_path, db, monkeypatch):
    (tmp_path / "-scan").mkdir()
    (tmp_path / "-scan" / "mal").write_bytes(SAMPLES["MD5"])
    monkeypatch.chdir(tmp_path)
    assert len(gav_core.scan("-scan", db_dir=db).threats) == 1


def test_cancel_stops_scan(target, db):
    for i in range(2000):
        (target / f"f{i}").write_bytes(os.urandom(64))
    cancel = threading.Event()
    summary = run(target, db, threads=1, cancel_event=cancel, on_start=lambda total: cancel.set())
    assert summary.cancelled and summary.scanned < 2000


def test_safe_display_escapes_control_and_bidi_characters():
    assert gav_core.safe_display("x\x1b[2K\r") == "x\\x1b[2K\\x0d"
    assert gav_core.safe_display("invoice‮gpj.exe") == "invoice\\x202egpj.exe"
