"""Pinned simulator configuration. Scores belong to the evaluator, not the agent."""

import subprocess
from pathlib import Path

BEHAVIOR_COMMIT = "b1979916ec1549b10a4e65e630bc6504a9af1b00"
RPENT_COMMIT = "886b3b274d3dd30bbc15615ea512d65ae90bc8b3"


def check_source(repo: Path, expected: str):
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                          capture_output=True, text=True, timeout=30)
    if head.stdout.strip() != expected:
        raise ValueError("Source revision differs from the audited protocol")
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                           cwd=repo, check=True, capture_output=True, text=True, timeout=30)
    if dirty.stdout.strip():
        raise ValueError("Audited source checkout has tracked modifications")


class NoActionPolicy:
    def set_action_dim(self, action_dim):
        self.action_dim = action_dim

    def reset(self):
        pass

    def forward(self, obs):
        raise RuntimeError("No action armed; never substitute zero absolute-joint commands")


def native_config(repo: Path):
    return {
        "env_wrapper": {"_target_": "omnigibson.eval.wrappers.RGBDFullResWrapper"},
        "policy_name": "matched-radio", "model": {
            "_target_": "experiments.behavior.native.NoActionPolicy"},
        "headless": True, "partial_scene_load": True, "max_steps": None,
        "write_video": False, "mode": "public_test", "seed": 0,
        "task": {"name": "turning_on_radio"},
        "robot_config_path": str(repo / "OmniGibson/omnigibson/eval/r1pro.yaml"),
    }
