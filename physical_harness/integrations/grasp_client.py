"""Bounded local inference transport. No network, retries, or motor authority."""
from __future__ import annotations

import os
import select
import signal
import subprocess
import time
import uuid

from physical_harness.core.actions import Verb, encode, integer, number, plain, strict_loads
from physical_harness.integrations.grasp_serde import proposal_from_dict


class GraspWorkerClient:
    def __init__(self, command: list[str], *, startup_timeout_s: float = 300,
                 expected_revision: str, max_bytes: int = 16000000):
        if os.name != "posix":
            raise RuntimeError("Inference worker transport requires POSIX")
        if type(command) is not list or not command or any(type(x) is not str or not x for x in command):
            raise ValueError("Explicit local command argv required; no shell")
        self.max_bytes = integer(max_bytes, low=128, high=32000000)
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=None, start_new_session=True)
        os.set_blocking(self.process.stdout.fileno(), False)
        os.set_blocking(self.process.stdin.fileno(), False)
        self.buffer, self.poisoned = b"", False
        try:
            hello = self._read(time.monotonic()+number(startup_timeout_s, low=.001))
            if hello != {"version": 1, "status": "ready", "revision": expected_revision}:
                raise ValueError("Unexpected/unpinned grasp worker")
        except BaseException:
            self.close()
            raise

    def _read(self, deadline):
        while b"\n" not in self.buffer:
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Grasp worker deadline")
            ready, _, _ = select.select([self.process.stdout], [], [], remaining)
            if ready:
                data = os.read(self.process.stdout.fileno(), 65536)
                if not data:
                    raise RuntimeError("Grasp worker closed without a response")
                self.buffer += data
                if len(self.buffer) > self.max_bytes:
                    raise ValueError("Grasp worker response exceeds bound")
        line, self.buffer = self.buffer.split(b"\n", 1)
        return strict_loads(line, max_bytes=self.max_bytes)

    def propose(self, cloud, *, timeout_s: float = 30, num_grasps: int = 64, top_k: int = 8):
        if self.poisoned:
            raise RuntimeError("Inference channel unresolved; no implicit retry")
        deadline = time.monotonic()+number(timeout_s, low=.001, high=300)
        integer(num_grasps, low=1, high=256)
        integer(top_k, low=1, high=min(num_grasps, 32))
        identifier = uuid.uuid4().hex
        payload = encode({"version": 1, "id": identifier, "cloud": plain(cloud),
                          "num_grasps": num_grasps, "top_k": top_k, "timeout_s": timeout_s})+b"\n"
        if len(payload) > self.max_bytes:
            raise ValueError("Grasp request exceeds byte budget")
        try:
            sent = 0
            while sent < len(payload):
                remaining = deadline-time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Grasp worker write deadline")
                _, ready, _ = select.select([], [self.process.stdin], [], remaining)
                if ready:
                    sent += os.write(self.process.stdin.fileno(), payload[sent:])
            response = self._read(deadline)
            if (set(response) != {"version", "id", "proposals", "error"}
                    or type(response["version"]) is not int or response["version"] != 1
                    or response["id"] != identifier):
                raise ValueError("Grasp worker response correlation mismatch")
            if response["error"] is not None:
                raise RuntimeError("Grasp inference failed; no automatic fallback")
            if type(response["proposals"]) is not list or len(response["proposals"]) > top_k:
                raise ValueError("Unexpected/unbounded grasp result")
            proposals = tuple(proposal_from_dict(p) for p in response["proposals"])
            for p in proposals:
                if p.intent.verb != Verb.GRASP or p.generator != "GraspGenX":
                    raise ValueError("Inference worker returned a non-grasp action")
                cloud.basis.require_same(p.basis)
                if (p.intent.entity, p.intent.part) != (cloud.entity, cloud.part):
                    raise ValueError("Grasp worker changed semantic target")
            return proposals
        except BaseException:
            self.poisoned = True
            self.close()
            raise

    def close(self):
        self.poisoned = True
        if not hasattr(self, "process"):
            return
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(self.process.pid, sig)
            except ProcessLookupError:
                pass
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
        for stream in (self.process.stdin, self.process.stdout):
            if stream and not stream.closed:
                stream.close()
        # Killing an inference worker has no relationship to robot stop acknowledgement.
