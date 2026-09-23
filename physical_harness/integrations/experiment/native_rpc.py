"""Bounded JSON-lines IPC for a simulator in its own Python environment.

POSIX only. Local worker termination is NOT a physical stop acknowledgement.
No pickle, shell expansion, remote URLs or implicit command retries are used.
"""
from __future__ import annotations

import base64
import importlib
import os
import select
import signal
import subprocess
import sys
import time
import uuid
from dataclasses import asdict

from physical_harness.core.contracts import SkillReceipt, SkillRequest
from physical_harness.integrations.experiment.native import (
    BeliefEstimate,
    CameraCapture,
    CoverageScan,
    NativeBindings,
    ObjectBox,
    Observation,
)
from physical_harness.integrations.experiment.validation import dumps, fields, loads, number, text

MAX_BYTES = 32_000_000


def load_factory(spec):
    module, sep, name = text(spec).partition(":")
    if not sep or not module or not name:
        raise ValueError("Use an operator-controlled module:factory")
    return getattr(importlib.import_module(module), name)


def encode_observation(obs):
    result = asdict(obs)
    result["cameras"] = [{"camera": c.camera, "data_b64": base64.b64encode(c.data).decode()}
                         for c in obs.cameras]
    return result


def decode_observation(value):
    fields(value, {"episode", "id", "sim_time", "cameras", "estimates", "boxes", "place_id",
                   "place_description", "coverage"}, {"legal_envelope"})
    cameras = []
    for c in value["cameras"]:
        fields(c, {"camera", "data_b64"})
        cameras.append(CameraCapture(c["camera"], base64.b64decode(c["data_b64"], validate=True)))
    boxes = [ObjectBox(**dict(b, box=tuple(b["box"]),
                              identity_candidates=tuple(b["identity_candidates"]))) for b in value["boxes"]]
    scans = [CoverageScan(**dict(s, targets=tuple(s["targets"]), cameras=tuple(s["cameras"])))
             for s in value["coverage"]]
    return Observation(value["episode"], value["id"], value["sim_time"], tuple(cameras),
                       tuple(BeliefEstimate(**e) for e in value["estimates"]), tuple(boxes),
                       value["place_id"], value["place_description"], tuple(scans),
                       value.get("legal_envelope"))


class ProcessNative:
    def __init__(self, command: list[str], *, episode: str, timeout_s: float = 60):
        if os.name != "posix":
            raise RuntimeError("Native subprocess transport currently requires POSIX")
        if not command or any(not isinstance(x, str) or not x for x in command):
            raise ValueError("Explicit command argument vector required")
        self.episode, self.timeout_s = text(episode), number(timeout_s, minimum=.01)
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=sys.stderr, start_new_session=True)
        os.set_blocking(self.process.stdout.fileno(), False)
        os.set_blocking(self.process.stdin.fileno(), False)
        self.poisoned, self._buffer = False, b""
        try:
            self.info = self._call("hello", {})
            if self.info.get("simulated") is not True:
                raise ValueError("This experiment runner only authorizes simulator backends")
        except Exception:
            self.close()
            raise

    def _call(self, method: str, arguments: dict, timeout_s: float | None = None):
        if self.poisoned:
            raise RuntimeError("Native channel is unresolved; restart only after operator review")
        request_id = uuid.uuid4().hex
        message = dumps({"version": 1, "episode": self.episode, "id": request_id,
                         "method": method, "arguments": arguments}) + b"\n"
        deadline = time.monotonic() + (self.timeout_s if timeout_s is None else min(self.timeout_s, timeout_s))
        try:
            sent = 0
            while sent < len(message):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Native request write deadline")
                _, writable, _ = select.select([], [self.process.stdin], [], remaining)
                if writable:
                    sent += os.write(self.process.stdin.fileno(), message[sent:])
            while b"\n" not in self._buffer:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Native response deadline; physical stop status unknown")
                readable, _, _ = select.select([self.process.stdout], [], [], remaining)
                if not readable:
                    continue
                part = os.read(self.process.stdout.fileno(), 65536)
                if not part:
                    raise RuntimeError("Native process closed without receipt")
                self._buffer += part
                if len(self._buffer) > MAX_BYTES:
                    raise ValueError("Native response exceeds size bound")
            line, self._buffer = self._buffer.split(b"\n", 1)
            reply = loads(line)
            fields(reply, {"version", "episode", "id", "result", "error"})
            if reply["version"] != 1 or reply["id"] != request_id or reply["episode"] != self.episode:
                raise ValueError("Native correlation/episode mismatch")
            if reply["error"] is not None:
                raise RuntimeError("Native operation failed; no implicit retry")
            return reply["result"]
        except Exception:
            self.poisoned = True
            raise

    def observe(self):
        return decode_observation(self._call("observe", {}))

    def run_skill(self, request):
        args = asdict(request)
        args["resources"] = sorted(request.resources)
        raw = self._call("run_skill", args, request.max_wall_s)
        fields(raw["metadata"], {"episode_id", "execution_epoch", "stop_acknowledged"})
        raw["evidence_ids"] = tuple(raw["evidence_ids"])
        raw["observed_predicates"] = tuple(raw["observed_predicates"])
        return SkillReceipt(**raw)

    def stop(self):
        if self.poisoned:
            return False
        return self._call("stop", {}, 5) is True

    def bindings(self):
        return NativeBindings(self.info["name"], self.observe, self.run_skill, self.stop,
                              simulated=True, qualification_id=self.info["qualification_id"])

    def close(self):
        # Reap the entire local simulator process group, including child workers.
        # This is NOT a remote physical stop acknowledgement.
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(self.process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.process.wait(timeout=2)
        self.process.stdin.close()
        self.process.stdout.close()


def serve(factory_spec: str, episode: str):
    from contextlib import redirect_stdout
    # Duplicate the protocol descriptor, then route even native/C stdout to stderr.
    protocol = os.fdopen(os.dup(sys.stdout.fileno()), "wb", buffering=0)
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    # Third-party simulator logs must never contaminate the JSON control channel.
    with redirect_stdout(sys.stderr):
        native = load_factory(factory_spec)(episode)
    if not isinstance(native, NativeBindings):
        raise TypeError("Factory must return NativeBindings")
    try:
        while True:
            raw = sys.stdin.buffer.readline(MAX_BYTES + 1)
            if not raw:
                break
            request = loads(raw)
            fields(request, {"version", "episode", "id", "method", "arguments"})
            if len(raw) > MAX_BYTES or request["version"] != 1 or request["episode"] != episode:
                raise ValueError("Invalid native request")
            result, error = None, None
            try:
                with redirect_stdout(sys.stderr):
                    if request["method"] == "hello":
                        result = {"name": native.name, "simulated": native.simulated,
                                  "qualification_id": native.qualification_id}
                    elif request["method"] == "observe":
                        result = encode_observation(native.observe())
                    elif request["method"] == "run_skill":
                        args = dict(request["arguments"])
                        args["resources"] = frozenset(args["resources"])
                        args["target_entities"] = tuple(args["target_entities"])
                        args["expected_predicates"] = tuple(args["expected_predicates"])
                        result = asdict(native.run_skill(SkillRequest(**args)))
                    elif request["method"] == "stop":
                        result = native.stop() is True
                    else:
                        raise ValueError("Unknown native operation")
            except Exception as exc:
                error = type(exc).__name__
            reply = dumps({"version": 1, "episode": episode, "id": request["id"],
                           "result": result, "error": error})
            if len(reply) > MAX_BYTES:
                raise ValueError("Native response too large")
            protocol.write(reply + b"\n")
            protocol.flush()
    finally:
        with redirect_stdout(sys.stderr):
            native.stop()
