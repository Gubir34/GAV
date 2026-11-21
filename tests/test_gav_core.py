import hashlib
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gav_core  # noqa: E402

SAMPLES = {"SHA256": b"GAV-TEST-ONE", "SHA1": b"GAV-TEST-TWO", "MD5": b"GAV-TEST-THREE"}


def signatures():
    return {algo: {hashlib.new(algo.lower(), data).hexdigest()} for algo, data in SAMPLES.items()}


def test_detects_all_three_algorithms(tmp_path):
    for algo, data in SAMPLES.items():
        (tmp_path / f"{algo}.bin").write_bytes(data)
    (tmp_path / "clean.txt").write_bytes(b"clean")
    summary = gav_core.scan(str(tmp_path), signatures=signatures())
    assert sorted(t.algo for t in summary.threats) == ["MD5", "SHA1", "SHA256"]
    assert summary.scanned == 4


def test_large_file_is_hashed_in_chunks(tmp_path):
    data = b"A" * (gav_core.CHUNK_SIZE * 3 + 7)
    (tmp_path / "big.bin").write_bytes(data)
    sigs = {"SHA256": {hashlib.sha256(data).hexdigest()}, "SHA1": set(), "MD5": set()}
    assert len(gav_core.scan(str(tmp_path), signatures=sigs).threats) == 1


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX only")
def test_fifo_and_symlinks_are_skipped(tmp_path):
    os.mkfifo(tmp_path / "pipe")
    os.symlink("/dev/zero", tmp_path / "zero")
    (tmp_path / "mal").write_bytes(SAMPLES["SHA256"])
    summary = gav_core.scan(str(tmp_path), signatures=signatures())
    assert summary.skipped == 2
    assert len(summary.threats) == 1


@pytest.mark.skipif(not hasattr(os, "geteuid") or os.geteuid() == 0, reason="needs a non-root POSIX user")
def test_unreadable_entries_are_reported(tmp_path):
    locked_file = tmp_path / "locked.bin"
    locked_file.write_bytes(SAMPLES["SHA256"])
    locked_file.chmod(0)
    locked_dir = tmp_path / "locked_dir"
    locked_dir.mkdir()
    locked_dir.chmod(0)
    try:
        summary = gav_core.scan(str(tmp_path), signatures=signatures())
    finally:
        locked_file.chmod(0o600)
        locked_dir.chmod(0o700)
    assert {os.path.basename(e.path) for e in summary.errors} == {"locked.bin", "locked_dir"}


def test_missing_database_refuses_to_scan(tmp_path):
    with pytest.raises(gav_core.NoSignaturesError):
        gav_core.load_signatures(str(tmp_path))


def test_load_signatures_from_db(tmp_path):
    conn = sqlite3.connect(tmp_path / gav_core.DB_FILES["MD5"])
    conn.execute("CREATE TABLE signatures (hash TEXT PRIMARY KEY, added_at TEXT)")
    conn.execute("INSERT INTO signatures VALUES ('ABCDEF', '')")
    conn.commit()
    conn.close()
    assert gav_core.load_signatures(str(tmp_path))["MD5"] == {"abcdef"}


def test_safe_display_escapes_control_characters():
    assert gav_core.safe_display("x\x1b[2K\r") == "x\\x1b[2K\\x0d"


def test_cancel_stops_scan(tmp_path):
    for i in range(5):
        (tmp_path / f"f{i}").write_bytes(b"x")
    worker = gav_core.ScanWorker(str(tmp_path))
    worker.cancel_event.set()
    summary = gav_core.scan(str(tmp_path), signatures=signatures(), cancel_event=worker.cancel_event)
    assert summary.cancelled and summary.scanned == 0
