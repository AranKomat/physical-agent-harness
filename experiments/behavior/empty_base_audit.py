"""Explicitly authorized empty-scene base response test, never a benchmark run."""

import argparse
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from .base_hold_audit import inspect
from .base_pulse import run_pulses
from .native import BEHAVIOR_COMMIT, check_source
from .observations import array


def fixture_posture(audit):
    """Copy only measured robot joint positions into a fresh calibration fixture.

    No base/world pose, object state, camera or task observation is imported.
    Native low-level order: six virtual joints, torso, arms, grippers.
    """
    if not audit.get("passed") or audit.get("source_revision") != BEHAVIOR_COMMIT:
        raise ValueError("Posture source must be a passed pinned native hold audit")
    sample = audit["hold_diagnostic"]["samples"][-1]
    if not sample["settled"]:
        raise ValueError("Posture source is not measured settled")
    p = np.asarray(sample["observation"]["proprio"], dtype=float)
    if p.shape != (61,) or not np.isfinite(p).all():
        raise ValueError("Invalid robot-only posture source")
    return [0.] * 6 + p[53:57].tolist() + p[3:10].tolist() + p[28:35].tolist() + p[24:26].tolist() + p[49:51].tolist()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-empty-scene-motion", action="store_true", required=True)
    parser.add_argument("--licenses-accepted", action="store_true", required=True)
    parser.add_argument("--spawn-height", type=float, choices=(0., .01, .05), default=.01,
                        help="Calibration-only floor-contact sensitivity condition, metres")
    parser.add_argument("--characterize-unsettled", action="store_true",
                        help="Empty-scene characterization only; can never pass qualification")
    parser.add_argument("--posture-from-audit", type=Path,
                        help="Use only settled robot joints from an earlier hold audit in this empty fixture")
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    check_source(source, BEHAVIOR_COMMIT)
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise ValueError("Empty-scene audit is restricted to simulator GPU 0")
    output.mkdir(parents=True, exist_ok=False)
    report = {"kind": "empty-scene-base-response-calibration", "passed": False,
              "benchmark_result": False, "benchmark_clearance_qualified": False,
              "motion_qualified": False, "model_calls": 0, "source_revision": BEHAVIOR_COMMIT,
              "setup_physics": "Environment construction and one env.reset; excluded from control counts",
              "ground_truth_pose_read": False,
              "scope": "User-authorized empty-scene component diagnostic only; not hybrid admission"}

    def save():
        (output / "audit.json").write_text(json.dumps(report, indent=2) + "\n")

    save()
    try:
        import omnigibson as og
        import torch
        from omegaconf import OmegaConf
        from omnigibson.eval.evaluator import Evaluator
        from omnigibson.eval.utils.eval_utils import seed_everything
        from omnigibson.macros import gm

        if source not in Path(og.__file__).resolve().parents:
            raise ValueError("Imported simulator source differs")
        gm.HEADLESS = True
        seed_everything(0)
        config_path = source / "OmniGibson/omnigibson/eval/r1pro.yaml"
        robot_config = OmegaConf.to_container(OmegaConf.load(config_path), resolve=True)
        robot_config.pop("eval", None)
        if args.posture_from_audit:
            posture_bytes = args.posture_from_audit.read_bytes()
            robot_config["reset_joint_pos"] = fixture_posture(json.loads(posture_bytes))
            report["posture_source_sha256"] = hashlib.sha256(posture_bytes).hexdigest()
            report["posture_source_scope"] = "Robot joint positions only; no base/world pose or scene state"
        robot_config.update(obs_modalities=["proprio"], position=[0., 0., args.spawn_height],
                            orientation=[0., 0., 0., 1.])
        config = {"env": {"action_frequency": 30, "rendering_frequency": 30,
                           "physics_frequency": 120, "automatic_reset": False},
                  "scene": {"type": "Scene", "use_floor_plane": True},
                  "robots": [robot_config], "objects": [], "task": {"type": "DummyTask"}}
        report["robot_config_source_sha256"] = hashlib.sha256(config_path.read_bytes()).hexdigest()
        report["config"] = config
        report["spawn_height_m"] = args.spawn_height
        report["runner_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        report["pulse_driver_sha256"] = hashlib.sha256(
            (Path(__file__).parent / "base_pulse.py").read_bytes()).hexdigest()
        save()
        env = og.Environment(configs=config)
        robot = env.robots[0]
        report["base_mass_before_eval_settings"] = float(robot.base_footprint_link.mass)
        # Reuse the pinned evaluator's robot-only mass adjustment. No task/scene
        # state or policy is loaded; the proprio-only fixture has no camera roles.
        Evaluator._apply_robot_eval_settings(SimpleNamespace(robot=robot, robot_camera_names={}))
        report["base_mass_after_eval_settings"] = float(robot.base_footprint_link.mass)
        report["setup_physics"] += "; pinned evaluator robot mass adjustment/stop/play"
        og.sim.update_handles()
        env.reset()
        # Match the pinned evaluator's pre-trial settling protocol, applied only
        # to our empty fixture robot. Never repeat this during a measured pulse.
        for _ in range(25):
            og.sim.step_physics()
            robot.keep_still()
        env.scene.update_initial_file()
        env.scene.reset()
        env.reset()
        report["setup_physics"] += "; 25 physics-only settle ticks with keep_still, scene snapshot/reset, second env.reset"
        report["setup_keep_still_physics_ticks"] = 25
        if len(env.robots) != 1 or env.scene.__class__.__name__ != "Scene":
            raise ValueError("Not the authorized empty calibration fixture")
        if not np.isclose(og.sim.get_sim_step_dt(), 1 / 30):
            raise ValueError("Native control timestep changed")
        p = array(robot.get_proprioception()[0])
        report["codec"] = inspect(robot, p)
        report["initial_proprio"] = p.tolist()
        save()

        def step(command):
            _, _, terminated, truncated, _ = env.step(torch.tensor(command, dtype=torch.float32))
            if terminated or truncated:
                raise RuntimeError("Empty-scene environment ended unexpectedly")
            return array(robot.get_proprioception()[0])

        def save_trial(state):
            report["trial"] = state
            save()

        result = run_pulses(p, step, report["codec"]["gripper_ranges"], save_trial,
                            characterize_unsettled=args.characterize_unsettled)
        report["passed"] = result["passed"]
        save()
    except BaseException as error:
        report.update(passed=False, error_type=type(error).__name__, error=str(error))
        save()
        raise
    finally:
        if "og" in locals() and og.sim is not None:
            save()
            og.shutdown()


if __name__ == "__main__":
    main()
