"""Sensor-only adapter for the pinned Behavior-Skill pi05-pt50-skill release."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np

from .contracts import Stamp
from .native import check_source

SOURCE_COMMIT = "7ca6eace02aaba2d8ce19af600b85dd04a60d720"
HF_REVISION = "98941096c94b0f978391d8a0accc699c32ec8b2a"
HF_REPO = "mafangniu/Behavior-Skill-VLA-Checkpoints"
CAMERAS = ("head", "left_wrist", "right_wrist")
MODEL_CAMERAS = ("base_0_rgb", "left_wrist_0_rgb", "right_wrist_0_rgb")


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def extract_state(proprio):
    """Match upstream state order, which differs from native action order."""
    p = np.asarray(proprio, dtype=np.float32)
    if p.shape != (61,) or not np.isfinite(p).all():
        raise ValueError("Expected finite native R1Pro proprio[61]")
    return np.concatenate((p[:3], p[53:57], p[3:10], p[28:35],
                           [p[24:26].sum(), p[49:51].sum()]))


def sensor_inputs(packet, resize):
    instruction = packet.get("instruction")
    if not isinstance(instruction, str) or not instruction.strip():
        raise ValueError("Explicit nonempty skill instruction required")
    rgb = packet.get("rgb")
    if not isinstance(rgb, dict) or set(rgb) != set(CAMERAS):
        raise ValueError("Exactly head/left_wrist/right_wrist RGB required")
    images = {}
    for camera, model_camera in zip(CAMERAS, MODEL_CAMERAS, strict=True):
        image = np.asarray(rgb[camera])
        if (image.ndim != 3 or image.shape[-1] != 3 or image.dtype != np.uint8
                or min(image.shape[:2]) < 1):
            raise ValueError("Expected HWC uint8 RGB")
        images[model_camera] = resize(image, 224, 224)
    return {"state": extract_state(packet.get("proprio")), "image": images,
            "image_mask": dict.fromkeys(MODEL_CAMERAS, np.True_), "prompt": instruction}


def verify_checkpoint(checkpoint, manifest):
    root = Path(checkpoint).resolve(strict=True)
    record = json.loads(Path(manifest).read_text())
    if (record.get("repo_id") != HF_REPO or record.get("revision") != HF_REVISION
            or record.get("prefix") != "pi05-pt50-skill"
            or record.get("verified") is not True):
        raise ValueError("Wrong or unverified Behavior-Skill manifest")
    files = record["files"]
    if len(files) != 727 or len({f["path"] for f in files}) != 727:
        raise ValueError("Unexpected checkpoint inventory")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual != {f["path"] for f in files}:
        raise ValueError("Checkpoint inventory differs from manifest")
    for entry in files:
        path = root / entry["path"]
        if path.is_symlink() or root not in path.resolve().parents:
            raise ValueError("Unsafe checkpoint path")
        if path.stat().st_size != entry["bytes"] or sha256(path) != entry["sha256"]:
            raise ValueError(f"Checkpoint hash mismatch: {entry['path']}")
    return record


class BehaviorSkillBackend:
    """No action queue or temporal ensemble; every call uses fresh observations."""

    def __init__(self, policy, resize, receipt=None):
        self.policy, self.resize, self.receipt = policy, resize, receipt
        self.stamp = None
        self.last_sequence = -1
        self.calls = []

    def reset(self, stamp):
        self.stamp = Stamp.model_validate(stamp)
        self.last_sequence = self.stamp.sequence - 1
        return {"stamp": self.stamp.model_dump()}

    def infer(self, packet):
        stamp = Stamp.model_validate(packet["stamp"])
        if (self.stamp is None or not stamp.same_episode(self.stamp)
                or stamp.sequence <= self.last_sequence):
            raise ValueError("Stale or uninitialized policy request")
        inputs = sensor_inputs(packet, self.resize)
        # Explicit per-observation noise makes later paired comparisons possible.
        noise_index = stamp.sequence - self.stamp.sequence
        noise = np.random.default_rng(20260920 + noise_index).standard_normal(
            (32, 32), dtype=np.float32
        )
        start = time.monotonic()
        output = self.policy.infer(inputs, noise=noise)
        actions = np.asarray(output["actions"])
        if actions.shape != (32, 32) or not np.isfinite(actions).all():
            raise ValueError("Expected finite 32x32 unnormalized model action chunk")
        actions = actions[:, :23]  # Upstream B1kOutputs removes only model padding.
        self.last_sequence = stamp.sequence
        self.calls.append({"stamp": stamp.model_dump(), "instruction": inputs["prompt"],
                           "noise_index_since_reset": noise_index,
                           "inference_s": time.monotonic() - start,
                           "action_shape": list(actions.shape)})
        if self.receipt:
            Path(self.receipt).write_text(json.dumps({"calls": self.calls,
                                                    "actions_sent_by_server": 0}, indent=2))
        return {"stamp": stamp.model_dump(), "actions": actions}


def load_backend(source, checkpoint, manifest, receipt):
    source, checkpoint = Path(source).resolve(), Path(checkpoint).resolve()
    check_source(source, SOURCE_COMMIT)
    verify_checkpoint(checkpoint, manifest)

    import jax
    import jax.numpy as jnp
    from openpi import transforms
    from openpi.models import model, pi0_config, tokenizer
    from openpi.policies.policy import Policy
    from openpi.shared import normalize
    from openpi_client.image_tools import resize_with_pad

    if source not in Path(model.__file__).resolve().parents:
        raise ValueError("Imported OpenPI is not the pinned Behavior-Skill source")
    if not all(d.platform == "gpu" for d in jax.devices()):
        raise ValueError("Behavior-Skill must use CUDA, not a silent CPU fallback")
    # Equivalent to pi05_b1k-base, but bypass the training loader and simulator
    # imports. Sensor inputs above implement its audited B1kInputs projection.
    cfg = pi0_config.Pi0Config(pi05=True, action_horizon=32)
    stats = normalize.load(checkpoint / "assets/behavior-1k/2025-challenge-demos")
    for name in ("state", "actions"):
        for field in ("mean", "std", "q01", "q99"):
            array = np.asarray(getattr(stats[name], field))
            if array.shape != (32,) or not np.isfinite(array).all():
                raise ValueError("Invalid checkpoint normalization statistics")
    start = time.monotonic()
    loaded = cfg.load(model.restore_params(checkpoint / "params", dtype=jnp.bfloat16))
    policy = Policy(loaded, transforms=[
        transforms.Normalize(stats, use_quantiles=True),
        transforms.ResizeImages(224, 224),
        transforms.TokenizePrompt(tokenizer.PaligemmaTokenizer(cfg.max_token_len),
                                  discrete_state_input=True),
        transforms.PadStatesAndActions(32),
    ], output_transforms=[transforms.Unnormalize(stats, use_quantiles=True)])
    Path(receipt).parent.mkdir(parents=True, exist_ok=True)
    Path(receipt).with_suffix(".load.json").write_text(json.dumps({
        "source_revision": SOURCE_COMMIT, "checkpoint_revision": HF_REVISION,
        "checkpoint": "pi05-pt50-skill", "load_s": time.monotonic() - start,
        "input": "legal RGB + proprio61", "motion_qualified": False,
        "training_overlap": "50-task BEHAVIOR-trained; not held-out motor generalization",
        "upstream_runtime": "JAX", "action_horizon": 32, "denoising_steps": 10,
        "manifest_sha256": sha256(manifest),
    }, indent=2))
    return BehaviorSkillBackend(policy, resize_with_pad, receipt)
