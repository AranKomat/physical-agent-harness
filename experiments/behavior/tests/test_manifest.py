import json

import pytest

from experiments.behavior.corvid_server import PREFIX, verify_checkpoint
from experiments.behavior.manifest import create_manifest


def test_integrity_manifest_rejects_tampering(tmp_path):
    checkpoint = tmp_path / "weights"
    files = checkpoint / PREFIX
    files.mkdir(parents=True)
    for i in range(40):
        (files / str(i)).write_text(str(i))
    manifest = tmp_path / "manifest.json"
    record = create_manifest("corvid", checkpoint, manifest)
    assert len(record["files"]) == 40
    verify_checkpoint(checkpoint, manifest)
    (files / "1").write_text("tampered")
    with pytest.raises(ValueError, match="Corrupt"):
        verify_checkpoint(checkpoint, manifest)


def test_inventory_failure_does_not_create_verified_manifest(tmp_path):
    checkpoint = tmp_path / "weights"
    checkpoint.mkdir()
    out = tmp_path / "manifest.json"
    with pytest.raises(ValueError, match="Inventory"):
        create_manifest("behavior-skill", checkpoint, out)
    assert not out.exists()


def test_manifest_path_escape_rejected(tmp_path):
    checkpoint = tmp_path / "weights"
    files = checkpoint / PREFIX
    files.mkdir(parents=True)
    for i in range(40):
        (files / str(i)).write_text(str(i))
    out = tmp_path / "manifest.json"
    record = create_manifest("corvid", checkpoint, out)
    record["files"][0]["path"] = "../outside"
    out.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        verify_checkpoint(checkpoint, out)
