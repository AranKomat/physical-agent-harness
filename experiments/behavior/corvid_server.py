"""Pinned all-task Corvid policy, using its published temporal-ensemble wrapper."""

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np

from experiments.behavior.behavior_skill import sha256
from experiments.behavior.ensemble_backend import EnsembleBackend
from experiments.behavior.native import check_source

SOURCE_COMMIT = "cc60a469a376397f6fb579087150d9e987b7e34e"
REVISION = "b627f22777d9babc6d4b06d7f088266dc484dd8c"
PREFIX = "backbone_foundation_100ep"


class NativeWrapper:
    """Normalize only the upstream return rank to the shared native RPC contract."""

    robot_obs = {"observation": {
        "head": "robot_r1::robot_r1:zed_link:Camera:0::rgb",
        "left_wrist": "robot_r1::robot_r1:left_realsense_link:Camera:0::rgb",
        "right_wrist": "robot_r1::robot_r1:right_realsense_link:Camera:0::rgb",
    }}

    def __init__(self, wrapper):
        self.wrapper = wrapper

    @property
    def text_prompt(self):
        return self.wrapper.text_prompt

    @text_prompt.setter
    def text_prompt(self, value):
        self.wrapper.text_prompt = value

    def reset(self):
        self.wrapper.reset()

    def act(self, packet):
        result = np.asarray(self.wrapper.act(packet))
        if result.shape != (1, 23):
            raise ValueError("Unexpected Corvid wrapper output")
        return result[0]


def verify_checkpoint(root, manifest):
    record = json.loads(manifest.read_text())
    if (record.get("repo_id") != "0Corvid0/pi05-b1k-families"
            or record.get("revision") != REVISION or record.get("verified") is not True):
        raise ValueError("Wrong Corvid manifest")
    files = record["files"]
    paths = {f["path"] for f in files}
    actual = {p.relative_to(root).as_posix() for p in (root / PREFIX).rglob("*") if p.is_file()}
    if len(files) != 40 or len(paths) != 40 or paths != actual:
        raise ValueError("Unexpected Corvid checkpoint inventory")
    for entry in files:
        path = root / entry["path"]
        if path.is_symlink() or root.resolve() not in path.resolve().parents:
            raise ValueError("Unsafe checkpoint path")
        if path.stat().st_size != entry["bytes"] or sha256(path) != entry["sha256"]:
            raise ValueError("Corrupt Corvid checkpoint")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "weights", "manifest", "receipt"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8011)
    args = parser.parse_args()
    if not os.environ.get("CUDA_VISIBLE_DEVICES", "").isdigit():
        raise ValueError("Policy requires one explicitly selected GPU")
    check_source(args.source, SOURCE_COMMIT)
    verify_checkpoint(args.weights, args.manifest)
    import jax
    import jax.numpy as jnp
    from openpi import transforms
    from openpi.models import model, pi0_config, tokenizer
    from openpi.policies.b1k_policy import B1kInputs, B1kOutputs
    from openpi.policies.policy import Policy
    from openpi.shared import normalize
    from openpi.shared.eval_b1k_wrapper import B1KPolicyWrapper

    from experiments.behavior.policy_server import PolicyFacade

    source = args.source.resolve() / "b1k-baselines/baselines/openpi"
    if source not in Path(model.__file__).resolve().parents:
        raise ValueError("Imported model is not the pinned Corvid runtime")
    if not all(d.platform == "gpu" for d in jax.devices()):
        raise ValueError("Corvid must use CUDA, not a silent CPU fallback")
    checkpoint = args.weights / PREFIX
    stats = normalize.load(checkpoint / "assets/behavior-1k/2026-challenge-demos")
    for name in ("state", "actions"):
        for field in ("mean", "std", "q01", "q99"):
            value = np.asarray(getattr(stats[name], field))
            if value.shape != (23,) or not np.isfinite(value).all():
                raise ValueError("Unexpected normalization statistics")
    start = time.monotonic()
    # Exact inference subset of LeRobotB1KDataConfig + ModelTransformFactory;
    # no training loader, demo dataset, simulator state, or config-side downloads.
    cfg = pi0_config.Pi0Config(pi05=True, action_horizon=32)
    loaded = cfg.load(model.restore_params(checkpoint / "params", dtype=jnp.bfloat16))
    policy = Policy(loaded, transforms=[
        B1kInputs(action_dim=cfg.action_dim, model_type=cfg.model_type),
        transforms.Normalize(stats, use_quantiles=True),
        transforms.ResizeImages(224, 224),
        transforms.TokenizePrompt(tokenizer.PaligemmaTokenizer(cfg.max_token_len),
                                  discrete_state_input=cfg.discrete_state_input),
        transforms.PadStatesAndActions(cfg.action_dim),
    ], output_transforms=[transforms.Unnormalize(stats, use_quantiles=True), B1kOutputs(23)])
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.with_suffix(".load.json").write_text(json.dumps({
        "source_revision": SOURCE_COMMIT, "checkpoint_revision": REVISION,
        "load_s": time.monotonic() - start, "action_horizon": 32,
        "recipe": "upstream temporal_ensemble, queue 10, replan every action",
        "input": "RGB + proprio61", "training_overlap": "100 BEHAVIOR tasks",
        "manifest_sha256": sha256(args.manifest),
    }, indent=2) + "\n")
    backend = EnsembleBackend(NativeWrapper(B1KPolicyWrapper(policy)), args.receipt)
    PolicyFacade(backend).serve(transport="http", host="127.0.0.1", port=args.port,
                                parent_watch=False, session_sweep_s=None)


if __name__ == "__main__":
    main()
