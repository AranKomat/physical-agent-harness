"""Integrity manifest for operator-downloaded pinned weights; not origin attestation."""

import json

from experiments.behavior.behavior_skill import HF_REPO, HF_REVISION, sha256
from experiments.behavior.behavior_skill import verify_checkpoint as verify_skill
from experiments.behavior.corvid_server import PREFIX, REVISION
from experiments.behavior.corvid_server import verify_checkpoint as verify_corvid


def create_manifest(candidate, checkpoint, output):
    checkpoint = checkpoint.resolve(strict=True)
    output = output.resolve()
    if checkpoint in output.parents:
        raise ValueError("Keep the manifest outside the checkpoint inventory")
    if candidate == "corvid":
        root = checkpoint / PREFIX
        record = {"repo_id": "0Corvid0/pi05-b1k-families", "revision": REVISION}
        verify = verify_corvid
    elif candidate == "behavior-skill":
        root = checkpoint
        record = {"repo_id": HF_REPO, "revision": HF_REVISION, "prefix": "pi05-pt50-skill"}
        verify = verify_skill
    else:
        raise ValueError("Unknown candidate")
    paths = sorted(p for p in root.rglob("*") if p.is_file())
    if len(paths) != (40 if candidate == "corvid" else 727):
        raise ValueError("Inventory differs from the pinned checkpoint")
    if any(p.is_symlink() or checkpoint not in p.resolve().parents for p in paths):
        raise ValueError("Unsafe checkpoint inventory")
    record.update(verified=True, provenance="operator-downloaded pinned snapshot; local hashes",
                  files=[{"path": p.relative_to(checkpoint).as_posix(),
                          "bytes": p.stat().st_size, "sha256": sha256(p)} for p in paths])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        stream.write(json.dumps(record, indent=2) + "\n")
    verify(checkpoint, output)
    return record
