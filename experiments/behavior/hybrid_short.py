"""A-short/B-short tiny-perturbation handoff diagnostic, not targeted staging.

Explicitly authorized simulator exploration with UNKNOWN clearance; no GPT,
truth reads, task-trained weight switching, or strict hybrid admission claims.
"""

import argparse
import hashlib
import json
import os
import time
import uuid
from pathlib import Path

import numpy as np

from physical_harness.localization import RGBDOdometry

from .base_hold_audit import inspect
from .base_pulse import run_pulses
from .behavior_skill import HF_REVISION, SOURCE_COMMIT
from .contracts import Observation, Stamp
from .head_depth_shadow import HeadDepthShadow
from .native import BEHAVIOR_COMMIT, check_source, native_config
from .observations import BehaviorObservationFilter, EvidenceStore, capture_intrinsics
from .preprocessing import verify_native_preprocessing
from .radio import selected_prefix

INSTRUCTION = "Move to the radio receiver on the table."
POLICY_ACTIONS = 384


def capture_record(evaluator, observation, shadow=None):
    calibration = capture_intrinsics(evaluator, observation)
    row = {"observation": observation.model_dump(), "calibration": calibration}
    if shadow is not None:
        row["head_depth_shadow"] = shadow.update(observation, calibration)
    return row


def execute_policy(transport, observation, store, step, capture, report, save, preprocessing):
    stamp = observation.stamp.model_dump()
    if transport.reset(stamp)["stamp"] != stamp:
        raise ValueError("Policy reset acknowledgement mismatch")
    started = time.monotonic()
    while report["policy_actions"] < POLICY_ACTIONS:
        if time.monotonic() - started > 900:
            raise TimeoutError("Short policy exposure exceeded wall budget")
        stamp = observation.stamp.model_dump()
        before = time.monotonic()
        reply = transport.infer({"stamp": stamp, "instruction": INSTRUCTION,
            "proprio": observation.proprio,
            "rgb": {camera: store.read(ref) for camera, ref in observation.rgb.items()}})
        actions = selected_prefix(reply, stamp, POLICY_ACTIONS - report["policy_actions"], 32)
        if not report["policy_chunks"]:
            report["preprocessing_proof"] = preprocessing(actions)
        report["policy_chunks"].append({"observation": observation.model_dump(),
            "native_start": report["native_actions"], "policy_start": report["policy_actions"],
            "inference_s": time.monotonic() - before, "actions": actions.tolist()})
        save()
        for action in actions:
            done = step(action)
            report["policy_actions"] += 1
            save()
            if done:
                report["native_end"] = True
                break
        observation = capture()
        if report.get("native_end"):
            break
    report["policy_wall_s"] = time.monotonic() - started
    return observation


def admit_perturbation_handoff(report):
    """Only this labeled diagnostic, never collision or navigation admission."""
    if not report["classical"]["passed"] or not report["classical"]["stop_acknowledged"]:
        raise ValueError("Classical pulse or measured stop failed")
    rows = report["captures"][-5:]
    if len(rows) != 5 or any("transform" not in r.get("head_depth_shadow", {}) for r in rows):
        raise ValueError("Missing live head-depth shadow at handoff")
    transforms = [RGBDOdometry._rigid(r["head_depth_shadow"]["transform"]) for r in rows]
    for transform in transforms[1:]:
        delta = np.linalg.inv(transforms[0]) @ transform
        angle = np.degrees(np.arccos(np.clip((np.trace(delta[:3, :3])-1)/2, -1, 1)))
        if np.linalg.norm(delta[:3, 3]) > .002 or angle > .2:
            raise ValueError("Head motion has not stabilized for the perturbation handoff")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--condition", choices=("A", "B"), required=True)
    parser.add_argument("--policy-load-receipt", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8011)
    for flag in ("allow-simulator", "allow-unknown-clearance-exploration", "licenses-accepted"):
        parser.add_argument("--" + flag, action="store_true", required=True)
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    check_source(source, BEHAVIOR_COMMIT)
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise ValueError("Simulator must use GPU 0")
    receipt = json.loads(args.policy_load_receipt.read_text())
    if (receipt.get("source_revision") != SOURCE_COMMIT
            or receipt.get("checkpoint_revision") != HF_REVISION):
        raise ValueError("Wrong frozen policy load receipt")
    output.mkdir(parents=True, exist_ok=False)
    report = {"passed": False, "benchmark_result": False, "motion_qualified": False,
              "scope": "tiny_perturbation_handoff_not_targeted_staging", "condition": args.condition,
              "clearance": "unknown", "strict_gates_overridden": False, "gpt_calls": 0,
              "native_actions": 0, "policy_actions": 0, "policy_chunks": [], "captures": [],
              "instruction": INSTRUCTION, "policy_action_ceiling": POLICY_ACTIONS,
              "policy_noise_index": "native_sequence_minus_handoff_reset_sequence",
              "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "policy_load_receipt": receipt,
              "policy_receipt_sha256": hashlib.sha256(args.policy_load_receipt.read_bytes()).hexdigest()}

    def save():
        (output / "hybrid_short.json").write_text(json.dumps(report, indent=2) + "\n")

    save()
    try:
        import omnigibson as og
        import open3d  # noqa: F401 - preload before capture freshness timing
        import torch
        from omegaconf import OmegaConf
        from omnigibson.eval.evaluator import Evaluator, resolve_instance_ids
        from omnigibson.eval.utils.eval_utils import seed_everything
        from omnigibson.macros import gm

        from .policy_server import HttpPolicyTransport

        if source not in Path(og.__file__).resolve().parents:
            raise ValueError("Imported simulator source mismatch")
        gm.HEADLESS = True
        seed_everything(0)
        cfg = native_config(source)
        cfg["robot"] = OmegaConf.load(cfg.pop("robot_config_path"))
        native_id = resolve_instance_ids("turning_on_radio", [0], mode="public_test")[0]
        if int(native_id) != 301:
            raise ValueError("Unexpected radio instance")
        with Evaluator(OmegaConf.create(cfg)) as evaluator:
            evaluator.reset()
            evaluator.load_task_instance(native_id)
            evaluator.reset()
            if not np.isclose(og.sim.get_sim_step_dt(), 1/30):
                raise ValueError("Native timestep changed")
            store = EvidenceStore(output / "evidence")
            ingress, shadow = BehaviorObservationFilter(store), HeadDepthShadow(store)
            stamp = Stamp(session=str(uuid.uuid4()), epoch=0, sequence=0)

            class Hook:
                action = None

                def forward(self, obs):
                    if self.action is None:
                        raise RuntimeError("No action armed")
                    action, self.action = self.action, None
                    return torch.tensor(action, dtype=torch.float32)

                def reset(self):
                    self.action = None

            hook = Hook()
            evaluator.policy = hook

            def capture(*, track=False):
                current = stamp.model_copy(update={"sequence": report["native_actions"]})
                observation = ingress.convert(evaluator.obs, current, time.monotonic())
                row = capture_record(evaluator, observation, shadow if track else None)
                report["captures"].append(row)
                save()
                return observation

            def step(action):
                hook.action = action
                terminated, truncated = evaluator.step()
                report["native_actions"] += 1
                save()
                return bool(terminated or truncated)

            evaluator.start_recording(str(output / "rollout.mp4"))
            observation = capture(track=args.condition == "B")
            report["codec"] = inspect(evaluator.robot, observation.proprio)
            if args.condition == "B":
                def classical_step(action):
                    if step(action):
                        raise RuntimeError("Episode ended before handoff")
                    return capture(track=True).proprio

                def save_classical(state):
                    report["classical"] = state
                    save()

                run_pulses(observation.proprio, classical_step, report["codec"]["gripper_ranges"],
                           save_classical, pulse_names=("forward",))
                admit_perturbation_handoff(report)
                observation = Observation.model_validate(report["captures"][-1]["observation"])
            report["handoff"] = {"observation": observation.model_dump(),
                "classical_actions": report["native_actions"], "target_distance": None,
                "target_distance_status": "not_measured_not_targeted_staging",
                "checkpoint_revision": HF_REVISION, "policy_reset_sequence": observation.stamp.sequence}
            save()
            final = execute_policy(HttpPolicyTransport(args.port), observation, store, step, capture,
                report, save, lambda actions: verify_native_preprocessing(evaluator.robot, actions))
            evaluator.stop_recording()
            report.update(passed=True, final_observation=final.model_dump(),
                          native_success_evaluation_only=bool(evaluator.env.task.success))
            save()
    except BaseException as error:
        report.update(passed=False, error_type=type(error).__name__, error=str(error))
        save()
        raise


if __name__ == "__main__":
    main()
