"""User-authorized simulator-only pulses with UNKNOWN clearance explicitly logged.

Not a collision qualification, task benchmark, or strict hybrid gate override.
Uses the ordinary radio evaluator and its fresh legal observation path.
"""

import argparse
import hashlib
import json
import os
import time
import uuid
from pathlib import Path

import numpy as np

from .base_hold_audit import inspect
from .base_pulse import PULSES, run_pulses
from .contracts import Stamp
from .native import BEHAVIOR_COMMIT, check_source, native_config
from .observations import BehaviorObservationFilter, EvidenceStore, capture_intrinsics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-simulator", action="store_true", required=True)
    parser.add_argument("--licenses-accepted", action="store_true", required=True)
    parser.add_argument("--allow-unknown-clearance-exploration", action="store_true", required=True)
    parser.add_argument("--pulses", nargs="+", choices=[p[0] for p in PULSES], default=["forward"])
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    check_source(source, BEHAVIOR_COMMIT)
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise ValueError("Exploratory simulator diagnostic is restricted to GPU 0")
    output.mkdir(parents=True, exist_ok=False)
    report = {"kind": "native-radio-exploratory-base-response", "passed": False,
              "benchmark_result": False, "motion_qualified": False, "model_calls": 0,
              "source_revision": BEHAVIOR_COMMIT, "native_id": 301,
              "clearance": {"status": "unknown", "certified_free": False,
                            "authorization": "explicit_simulator_only_exploration",
                            "strict_default_gates_overridden": False},
              "setup_physics": "ordinary evaluator reset/load/reset before counted actions",
              "native_steps_completed": 0, "captures": [],
              "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "pulse_driver_sha256": hashlib.sha256((Path(__file__).parent / "base_pulse.py").read_bytes()).hexdigest()}

    def save():
        (output / "audit.json").write_text(json.dumps(report, indent=2) + "\n")

    save()
    try:
        import omnigibson as og
        import torch
        from omegaconf import OmegaConf
        from omnigibson.eval.evaluator import Evaluator, resolve_instance_ids
        from omnigibson.eval.utils.eval_utils import seed_everything
        from omnigibson.macros import gm

        if source not in Path(og.__file__).resolve().parents:
            raise ValueError("Imported simulator source differs")
        gm.HEADLESS = True
        seed_everything(0)
        config = native_config(source)
        config["robot"] = OmegaConf.load(config.pop("robot_config_path"))
        native_id = resolve_instance_ids("turning_on_radio", [0], mode="public_test")[0]
        if int(native_id) != 301:
            raise ValueError("Unexpected native radio instance")
        with Evaluator(OmegaConf.create(config)) as evaluator:
            evaluator.reset()
            evaluator.load_task_instance(native_id)
            evaluator.reset()
            if not np.isclose(og.sim.get_sim_step_dt(), 1 / 30):
                raise ValueError("Native timestep changed")
            store = EvidenceStore(output / "evidence")
            ingress = BehaviorObservationFilter(store)
            stamp = Stamp(session=str(uuid.uuid4()), epoch=0, sequence=0)

            def capture():
                current = ingress.convert(evaluator.obs, stamp, time.monotonic())
                report["captures"].append({"observation": current.model_dump(),
                    "camera_calibration": capture_intrinsics(evaluator, current),
                    "clearance_status": "unknown"})
                save()
                return current

            observation = capture()
            report["codec"] = inspect(evaluator.robot, observation.proprio)
            save()

            class PulsePolicy:
                command = None

                def reset(self):
                    self.command = None

                def forward(self, obs):
                    if self.command is None:
                        raise RuntimeError("No exploratory action supplied")
                    return torch.tensor(self.command, dtype=torch.float32)

            evaluator.policy = PulsePolicy()

            def step(command):
                nonlocal stamp
                evaluator.policy.command = command
                terminated, truncated = evaluator.step()
                # Persist native execution independently of downstream capture success.
                report["native_steps_completed"] += 1
                save()
                if terminated or truncated:
                    raise RuntimeError("Native episode ended during exploratory diagnostic")
                stamp = stamp.model_copy(update={"sequence": stamp.sequence + 1})
                return np.asarray(capture().proprio)

            def save_trial(state):
                report["trial"] = state
                save()

            result = run_pulses(observation.proprio, step, report["codec"]["gripper_ranges"],
                                save_trial, pulse_names=args.pulses)
            report["passed"] = result["passed"]
            save()
    except BaseException as error:
        report.update(passed=False, error_type=type(error).__name__, error=str(error))
        save()
        raise


if __name__ == "__main__":
    main()
