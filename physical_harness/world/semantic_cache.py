"""Reuse existing exact-dependency representation cache without broadening authority."""
from __future__ import annotations

from physical_harness.core.actions import digest, encode, ids, strict_loads, text
from physical_harness.world.representation_cache import Dependency, RepresentationCache


class SemanticRepresentationCache:
    """Exact source/prompt/model/schema cache for historical semantics and descriptors.

    Cached semantic output is never a fresh observation. Callers must rebind the
    original source request; repeating a cached prediction is not independent
    evidence. Geometry/plans/collision approval are deliberately unsupported.
    """
    ALLOWED = frozenset({"image_encoding", "crop_embedding", "semantic_annotation", "map_summary"})

    def __init__(self, maximum=32):
        self.cache = RepresentationCache(maximum=maximum)

    @staticmethod
    def dependencies(*, episode: str, model: str, preprocessing: str,
                     contents: tuple[str, ...], prompt: str, schema: str, scope_revision: str):
        ids(contents, empty=False)
        for s in (episode, model, preprocessing, prompt, schema, scope_revision):
            text(s, limit=32000)
        return (Dependency("episode", episode), Dependency("model", model),
                Dependency("preprocess", preprocessing), Dependency("content", digest(contents)),
                Dependency("prompt", digest(prompt)), Dependency("schema", schema),
                Dependency("scope", scope_revision))

    def put(self, kind: str, deps: tuple[Dependency, ...], value: dict, *, now: float, ttl_s: float):
        if kind not in self.ALLOWED:
            raise PermissionError("Never cache actions, poses or safety/semantic completion authority")
        # Immutable JSON prevents mutation of cached model/descriptor metadata.
        raw = encode(value)
        if len(raw) > 64000:
            raise ValueError("Representation cache entry exceeds byte budget")
        tagged = deps + (Dependency("kind", kind),)
        self.cache.put("reference_descriptor", tagged, raw, now=now, ttl_s=ttl_s)

    def get(self, kind, deps, *, now):
        if kind not in self.ALLOWED:
            raise PermissionError("Disallowed representation reuse")
        raw = self.cache.get("reference_descriptor", deps+(Dependency("kind", kind),), now=now)
        return None if raw is None else strict_loads(raw, max_bytes=64000)

    def report(self):
        return {"hits": self.cache.hits, "misses": self.cache.misses,
                "evictions": self.cache.evictions, "current_entries": len(self.cache.entries),
                "cross_frame_feature_reuse_implemented": False}
