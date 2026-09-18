"""Immutable content-addressed artifacts; references, not binaries, enter context."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


class EvidenceStore:
    def __init__(self, root: str | Path, max_artifact_bytes: int = 64 * 1024**2):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.limit = max_artifact_bytes

    def put(self, data: bytes, suffix: str) -> str:
        if suffix not in {".png", ".jpg", ".npy", ".json", ".mp4", ".txt"}:
            raise ValueError("Unsupported evidence format")
        if not isinstance(data, bytes) or not data or len(data) > self.limit:
            raise ValueError("Artifact must be nonempty bounded bytes")
        name = hashlib.sha256(data).hexdigest() + suffix
        path = self.root / name
        try:
            with path.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            if self.read(name) != data:
                raise ValueError("Existing evidence content mismatch") from None
        return name

    def read(self, name: str) -> bytes:
        path = self.root / name
        if path.parent.resolve() != self.root or path.is_symlink() or Path(name).name != name:
            raise ValueError("Invalid evidence reference")
        if path.stat().st_size > self.limit:
            raise ValueError("Artifact exceeds size limit")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != path.stem:
            raise ValueError("Evidence content hash mismatch")
        return data
