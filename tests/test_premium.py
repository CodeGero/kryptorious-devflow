import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from devflow import license as lic  # noqa: E402


# A valid key: payload groups + correct CRC32-based checksum group.
def _make_valid_key():
    groups = ["AB12", "CD34", "EF56"]
    chk = lic._checksum_groups(groups)
    return f"KRYP-{groups[0]}-{groups[1]}-{groups[2]}-{chk}"


def test_valid_key_passes():
    key = _make_valid_key()
    assert lic.is_valid_key(key)
    assert lic.is_valid_key(key.lower())  # case-insensitive normalize


def test_malformed_keys_rejected():
    for bad in ["", "KRYP-AB12-CD34", "NOPE-AB12-CD34-EF56-0000",
                "KRYP-AB12-CD34-EF56-XXXX", "KRYP-AB12-CD34-EF56-123"]:
        assert not lic.is_valid_key(bad), bad


def test_wrong_checksum_rejected():
    key = _make_valid_key()
    base = key.rsplit("-", 1)[0]
    assert not lic.is_valid_key(f"{base}-ZZZZ")


def test_activate_persists_and_unlocks(tmp_path, monkeypatch):
    monkeypatch.setattr(lic, "LICENSE_DIR", tmp_path / "cfg")
    monkeypatch.setattr(lic, "LICENSE_FILE", tmp_path / "cfg" / "license")
    key = _make_valid_key()
    assert lic.activate(key) is True
    assert (tmp_path / "cfg" / "license").read_text().strip() == key
    # stored key now unlocks require_premium
    assert lic.require_premium(None) is True


def test_require_premium_blocked_without_key(monkeypatch, capsys):
    monkeypatch.setattr(lic, "LICENSE_FILE", tmp_path_marker := Path("/nonexistent_xyz/license"))
    # no stored key -> blocked; should print upsell, return False
    assert lic.require_premium(None) is False
    out = capsys.readouterr().out
    assert "Premium required" in out or "Premium" in out


def test_premium_generates_artifacts(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(lic, "LICENSE_DIR", tmp_path / "cfg")
    monkeypatch.setattr(lic, "LICENSE_FILE", tmp_path / "cfg" / "license")
    key = _make_valid_key()
    assert lic.activate(key)

    from devflow.commands import premium as prem
    ok = prem.generate_premium(str(tmp_path / "proj"), deploy="docker", key=key)
    assert ok is True
    proj = tmp_path / "proj"
    assert (proj / "Dockerfile").exists()
    assert (proj / "docker-compose.yml").exists()
    assert (proj / ".github" / "workflows" / "ci-premium.yml").exists()
    assert (proj / "iac" / "main.staging.tf").exists()
    assert (proj / "iac" / "main.production.tf").exists()
    # approval gate present for production
    wf = (proj / ".github" / "workflows" / "ci-premium.yml").read_text()
    assert "environment: {name: production" in wf


def test_premium_blocked_without_license(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(lic, "LICENSE_FILE", tmp_path / "nope" / "license")
    from devflow.commands import premium as prem
    ok = prem.generate_premium(str(tmp_path / "proj2"), deploy="docker", key=None)
    assert ok is False
    assert not (tmp_path / "proj2" / "Dockerfile").exists()
