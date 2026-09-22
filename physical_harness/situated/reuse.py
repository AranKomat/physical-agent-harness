"""Exact dependency reuse for representations, NEVER stale metric action reuse.

This cache avoids known-identical work. No claim that similar frames have
interchangeable features, that static background means static contact, or that
an unchanged map makes an old grasp executable.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass

from ..action_compiler.types import digest, ids, integer, number, text


@dataclass(frozen=True)
class Dependency:
    name: str
    revision: str

    def __post_init__(self):
        text(self.name)
        text(self.revision)


class RepresentationCache:
    ALLOWED = frozenset({"image_encoding", "reference_descriptor", "graph_template"})

    def __init__(self, *, maximum=32, dispose=lambda value: None):
        integer(maximum, low=1, high=4096)
        self.maximum, self.dispose = maximum, dispose
        self.entries = {}
        self.hits = self.misses = self.evictions = 0
        self.lock = threading.RLock()

    def _key(self, kind, deps):
        if kind not in self.ALLOWED:
            raise PermissionError("Only reusable representations, never motion/geometry authority")
        if type(deps) is not tuple or not deps or not all(isinstance(d, Dependency) for d in deps):
            raise ValueError("Explicit immutable dependency set required")
        ids(tuple(d.name for d in deps))
        names = {d.name for d in deps}
        if not {"episode", "model", "preprocess", "content"} <= names:
            raise ValueError("Pin episode, model, preprocessing and exact content digest")
        return digest([kind, tuple(sorted(deps, key=lambda d: d.name))])

    def get(self, kind, dependencies, *, now):
        number(now, low=0)
        key = self._key(kind, dependencies)
        with self.lock:
            row = self.entries.pop(key, None)
            if row is None:
                self.misses += 1
                return None
            value, expires, deps, inserted = row
            if now < inserted or now >= expires:
                self.dispose(value)
                self.evictions += 1
                self.misses += 1
                return None
            self.entries[key] = row
            self.hits += 1
            return value

    def put(self, kind, dependencies, value, *, now, ttl_s):
        number(now, low=0)
        number(ttl_s, low=.001, high=3600)
        key = self._key(kind, dependencies)
        with self.lock:
            old = self.entries.pop(key, None)
            if old is not None:
                self.dispose(old[0])
            while len(self.entries) >= self.maximum:
                self.dispose(self.entries.pop(next(iter(self.entries)))[0])
                self.evictions += 1
            self.entries[key] = (value, now+ttl_s, dependencies, now)

    def invalidate(self, dependency_name):
        with self.lock:
            for key, row in tuple(self.entries.items()):
                if any(d.name == dependency_name for d in row[2]):
                    self.dispose(self.entries.pop(key)[0])
                    self.evictions += 1

    def close(self):
        with self.lock:
            for row in self.entries.values():
                self.dispose(row[0])
            self.entries.clear()
