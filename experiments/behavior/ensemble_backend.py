"""Sensor-only RPC adapter for the upstream temporal temporal-ensemble wrapper."""

import json
import threading
import time
from pathlib import Path

import numpy as np

from .contracts import Stamp


class EnsembleBackend:
    def __init__(self, wrapper, receipt=None):
        self.wrapper = wrapper
        self.receipt = Path(receipt) if receipt else None
        self.lock = threading.Lock()
        self.stamp = None
        self.last_sequence = -1
        self.instruction = None

    def reset(self, stamp):
        stamp = Stamp.model_validate(stamp)
        with self.lock:
            self.stamp = None
            self.wrapper.reset()
            self.stamp = stamp
            self.last_sequence = stamp.sequence - 1
            self.instruction = None
        return {"stamp": stamp.model_dump()}

    def infer(self, packet):
        with self.lock:
            stamp = Stamp.model_validate(packet["stamp"])
            if (self.stamp is None or not stamp.same_episode(self.stamp)
                    or stamp.sequence <= self.last_sequence):
                raise ValueError("Stale or uninitialized policy request")
            instruction = packet.get("instruction")
            if not isinstance(instruction, str) or not instruction.strip():
                raise ValueError("Explicit instruction required")
            proprio = np.asarray(packet.get("proprio"), dtype=np.float32)
            if proprio.shape != (61,) or not np.isfinite(proprio).all():
                raise ValueError("Expected finite native proprio[61]")
            cameras = self.wrapper.robot_obs["observation"]
            rgb = packet.get("rgb")
            if not isinstance(rgb, dict) or set(rgb) != set(cameras):
                raise ValueError("Exactly the three native RGB cameras required")
            inputs = {"robot_r1::proprio": proprio}
            for camera, key in cameras.items():
                image = np.asarray(rgb[camera])
                if (image.ndim != 3 or image.shape[-1] != 3
                        or image.dtype != np.uint8 or min(image.shape[:2]) < 1):
                    raise ValueError("Expected HWC uint8 RGB")
                inputs[key] = image
            start = time.monotonic()
            try:
                if instruction != self.instruction:
                    self.wrapper.reset()
                    self.wrapper.text_prompt = instruction
                    self.instruction = instruction
                # Upstream wrapper already unnormalizes absolute native actions.
                action = np.asarray(self.wrapper.act(inputs), dtype=np.float32)
                if action.shape != (23,) or not np.isfinite(action).all():
                    raise ValueError("Expected one finite native action[23]")
                self.last_sequence = stamp.sequence
                if self.receipt:
                    with self.receipt.open("a") as stream:
                        stream.write(json.dumps({"stamp": stamp.model_dump(),
                                                 "instruction": instruction,
                                                 "inference_s": time.monotonic() - start}) + "\n")
            except Exception:
                # An ambiguous failure may have advanced the temporal ensemble.
                self.stamp = None
                raise
            return {"stamp": stamp.model_dump(), "actions": action[None, :]}
