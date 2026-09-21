"""Explicit GraspGenX JSON-lines worker. Never controls a robot or calls GPT.

Run in a separately provisioned, OS-level no-egress container. Local paths and
licenses are startup settings, not model-supplied request fields. Third-party
stdout (including C-level output) is redirected away from the protocol channel.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from .graspgenx import LocalAssets, load_local
from .serde import cloud_from_dict, gripper_from_dict
from .types import encode, integer, number, plain, strict_loads, text

MAX_BYTES = 16000000


def serve(adapter, input_stream, output_stream):
    output_stream.write(encode({"version": 1, "status": "ready", "revision": adapter.revision})+b"\n")
    output_stream.flush()
    for line in iter(lambda: input_stream.readline(MAX_BYTES+1), b""):
        if len(line) > MAX_BYTES or not line.endswith(b"\n"):
            raise ValueError("Oversized/unterminated inference request")
        request = strict_loads(line, max_bytes=MAX_BYTES)
        if set(request) != {"version", "id", "cloud", "num_grasps", "top_k", "timeout_s"}:
            raise ValueError("Unexpected inference fields")
        if type(request["version"]) is not int or request["version"] != 1:
            raise ValueError("Unsupported inference protocol")
        identifier = text(request["id"])
        try:
            cloud = cloud_from_dict(request["cloud"])
            proposals = adapter.propose(cloud, deadline=time.monotonic()+number(request["timeout_s"], low=.001, high=300),
                                         num_grasps=integer(request["num_grasps"], low=1, high=256),
                                         top_k=integer(request["top_k"], low=1, high=32))
            response = {"version": 1, "id": identifier, "proposals": plain(proposals), "error": None}
        except Exception as error:
            response = {"version": 1, "id": identifier, "proposals": [], "error": type(error).__name__}
        payload = encode(response)
        if len(payload) > MAX_BYTES:
            raise ValueError("Oversized inference response")
        output_stream.write(payload+b"\n")
        output_stream.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--allow-inference", action="store_true")
    parser.add_argument("--licenses-accepted", action="store_true")
    args = parser.parse_args()
    if not args.allow_inference or not args.licenses_accepted:
        raise PermissionError("Explicit inference and license opt-ins required")
    cfg = strict_loads(args.config.read_bytes(), max_bytes=2000000)
    if set(cfg) != {"assets", "gripper", "expected_gripper_fingerprint",
                    "checkpoint_manifest", "gripper_manifest"}:
        raise ValueError("Unexpected worker config fields")
    values = dict(cfg["assets"])
    for key in ("source", "checkpoint_root", "gripper_root", "assets_dir"):
        values[key] = Path(values[key]).expanduser()
        if not values[key].is_absolute():
            raise ValueError("Worker configuration paths must be absolute")
    # No logs or exceptions can contaminate protocol stdout, even native libraries.
    protocol = os.fdopen(os.dup(sys.stdout.fileno()), "wb", buffering=0)
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    adapter = load_local(LocalAssets(**values), gripper_from_dict(cfg["gripper"]),
                         checkpoint_manifest=cfg["checkpoint_manifest"],
                         gripper_manifest=cfg["gripper_manifest"],
                         expected_gripper_fingerprint=cfg["expected_gripper_fingerprint"],
                         allow_inference=True, licenses_accepted=True)
    try:
        serve(adapter, sys.stdin.buffer, protocol)
    finally:
        protocol.close()


if __name__ == "__main__":
    main()
