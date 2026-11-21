"""Tests for install_gavcore.py using a fake release served from file:// URLs."""
import hashlib
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gav_core  # noqa: E402
import install_gavcore as inst  # noqa: E402

PAYLOAD = b"#!/bin/sh\necho gavcore 9.9.9\n"


@pytest.mark.parametrize("system,machine,asset", [
    ("Linux", "x86_64", "gavcore-linux-x86_64"),
    ("Linux", "aarch64", "gavcore-linux-arm64"),
    ("Darwin", "arm64", "gavcore-macos-arm64"),
    ("Windows", "AMD64", "gavcore-windows-x64.exe"),
    ("Windows", "ARM64", "gavcore-windows-x64.exe"),
])
def test_asset_name(system, machine, asset):
    assert inst.asset_name(system, machine) == asset


@pytest.mark.parametrize("system,machine", [("Darwin", "x86_64"), ("Linux", "riscv64"), ("FreeBSD", "amd64")])
def test_unsupported_platforms(system, machine):
    with pytest.raises(inst.InstallError):
        inst.asset_name(system, machine)


@pytest.fixture
def release(tmp_path):
    rel = tmp_path / "release" / "v9.9.9"
    rel.mkdir(parents=True)
    (rel / "gavcore-test").write_bytes(PAYLOAD)
    lock = {
        "version": "9.9.9",
        "base_url": (tmp_path / "release").as_uri() + "/v{version}/",
        "assets": {"gavcore-test": hashlib.sha256(PAYLOAD).hexdigest()},
    }
    return rel, lock


def test_install_verified(tmp_path, release):
    _, lock = release
    target = inst.install(str(tmp_path / "bin"), lock=lock, asset="gavcore-test")
    assert open(target, "rb").read() == PAYLOAD
    assert os.path.basename(target) == inst.EXE
    if os.name != "nt":
        assert os.access(target, os.X_OK)
    assert [f for f in os.listdir(tmp_path / "bin") if f.startswith(".gavcore-")] == []


def test_tampered_download_is_rejected(tmp_path, release):
    rel, lock = release
    (rel / "gavcore-test").write_bytes(PAYLOAD + b"evil")
    with pytest.raises(inst.IntegrityError):
        inst.install(str(tmp_path / "bin"), lock=lock, asset="gavcore-test")
    assert not (tmp_path / "bin" / inst.EXE).exists()


def test_existing_binary_survives_failed_update(tmp_path, release):
    rel, lock = release
    inst.install(str(tmp_path / "bin"), lock=lock, asset="gavcore-test")
    (rel / "gavcore-test").write_bytes(b"evil")
    with pytest.raises(inst.IntegrityError):
        inst.install(str(tmp_path / "bin"), lock=lock, asset="gavcore-test")
    assert (tmp_path / "bin" / inst.EXE).read_bytes() == PAYLOAD


def test_missing_pin_is_refused(tmp_path, release):
    _, lock = release
    lock["assets"] = {}
    with pytest.raises(inst.InstallError, match="No pinned SHA256"):
        inst.install(str(tmp_path / "bin"), lock=lock, asset="gavcore-test")


def test_oversized_download_is_refused(tmp_path, release):
    rel, lock = release
    with pytest.raises(inst.InstallError, match="too large"):
        inst.download((rel / "gavcore-test").as_uri(), limit=4)


def test_parse_sha256sums():
    text = "aa" * 32 + "  gavcore-linux-x86_64\n" + "BB" * 32 + " *gavcore-windows-x64.exe\n"
    assert inst.parse_sha256sums(text) == {"gavcore-linux-x86_64": "aa" * 32, "gavcore-windows-x64.exe": "bb" * 32}


def test_lock_file_is_valid():
    lock = inst.load_lock()
    assert lock["version"] and "{version}" in lock["base_url"]
    for asset, sha in lock["assets"].items():
        assert asset.startswith("gavcore-") and len(sha) == 64


@pytest.mark.skipif(os.name == "nt", reason="uses a POSIX shell script as a fake engine")
def test_find_engine_ignores_current_directory(tmp_path, monkeypatch):
    fake = tmp_path / "gavcore"
    fake.write_bytes(PAYLOAD)
    fake.chmod(0o755)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GAVCORE", raising=False)
    monkeypatch.setenv("PATH", os.pathsep.join([".", ""]))
    monkeypatch.setattr(gav_core, "_install_dirs", lambda: [])
    with pytest.raises(gav_core.EngineNotFoundError):
        gav_core.find_engine()
    monkeypatch.setenv("PATH", str(tmp_path))
    assert gav_core.find_engine() == str(fake)


@pytest.mark.skipif(os.name == "nt", reason="uses a POSIX shell script as a fake engine")
def test_engine_version(tmp_path):
    fake = tmp_path / "gavcore"
    fake.write_bytes(PAYLOAD)
    fake.chmod(0o755)
    assert inst.engine_version(str(fake)) == "9.9.9"
