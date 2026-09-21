"""Native codec audit; optional explicit bounded stationary-hold diagnostic."""

import argparse
import json
import os
import time
import uuid
from pathlib import Path

import numpy as np

from physical_harness.hybrid_v0.classical import BodyTwist

from .base_hold import base_hold, settled
from .contracts import Stamp
from .native import BEHAVIOR_COMMIT, check_source, native_config
from .observations import BehaviorObservationFilter, EvidenceStore, array

LAYOUT = {
    "base": (0, 3, "HolonomicBaseJointController"),
    "trunk": (3, 7, "JointController"),
    "arm_left": (7, 14, "JointController"),
    "gripper_left": (14, 15, "MultiFingerGripperController"),
    "arm_right": (15, 22, "JointController"),
    "gripper_right": (22, 23, "MultiFingerGripperController"),
}


def stationary_hold(evaluator, observation, store, gripper_ranges, max_steps, save):
    """At most 60 explicit hold ticks. Not navigation or moving-base braking."""
    import torch

    if type(max_steps) is not int or not 1 <= max_steps <= 60:
        raise ValueError("Stationary hold diagnostic requires 1..60 ticks")
    p0 = np.asarray(observation.proprio)
    command = base_hold(p0, BodyTwist(0, 0, 0), gripper_ranges=gripper_ranges)
    state = {"actions_attempted": 0, "actions_executed": 0, "settled": False,
             "physical_s": 0, "samples": [], "navigation_qualified": False}

    class Hold:
        def reset(self):
            pass

        def forward(self, obs):
            return torch.tensor(command, dtype=torch.float32)

    evaluator.policy = Hold()
    ingress = BehaviorObservationFilter(store)
    consecutive = 0
    for step in range(max_steps):
        state["actions_attempted"] += 1
        save(state)
        terminated, truncated = evaluator.step()
        state["actions_executed"] += 1
        state["physical_s"] = state["actions_executed"] / 30
        current = ingress.convert(evaluator.obs, observation.stamp.model_copy(
            update={"sequence": step + 1}), time.monotonic())
        p = np.asarray(current.proprio)
        indices = [*range(3, 10), *range(28, 35), *range(53, 57)]
        drift = float(np.max(abs(p[indices] - p0[indices])))
        at_rest = settled(p)
        state["samples"].append({"sequence": step + 1, "settled": at_rest,
                                 "joint_drift": drift, "observation": current.model_dump()})
        consecutive = consecutive + 1 if at_rest else 0
        if drift > .03 or np.linalg.norm(p[:2]) > .02 or abs(p[2]) > .04:
            state["stop_reason"] = "hold_drift_limit"
            save(state)
            raise RuntimeError("Stationary hold drift exceeded diagnostic limit")
        if terminated or truncated:
            state["stop_reason"] = "native_end"
            save(state)
            raise RuntimeError("Native episode ended during hold diagnostic")
        if consecutive >= 5:
            state.update(settled=True, stop_reason="five_consecutive_settled_samples")
            save(state)
            return state
        save(state)
    state["stop_reason"] = "hold_budget_exhausted"
    save(state)
    return state


def inspect(robot, proprio):
    import torch
    from omnigibson.controllers import controller_view
    from omnigibson.controllers.controller_view import ControllerView as View

    cb = controller_view.cb
    if robot.action_dim != 23 or set(robot.controllers) != set(LAYOUT):
        raise ValueError("Unexpected native layout")
    if robot._action_normalize is not False:
        raise ValueError("Unexpected robot-level action normalization")
    reference = np.empty(23)
    controllers, gripper_ranges, records = {}, [], {}
    for name, (lo, hi, typename) in LAYOUT.items():
        group, member = robot.controllers[name]
        controller = View._controller_groups[group]
        if type(controller).__name__ != typename:
            raise ValueError("Controller class changed")
        np.testing.assert_array_equal(array(robot.controller_action_idx[name]), np.arange(lo, hi))
        reference[lo:hi] = array(View.compute_no_op_action(group, member))
        inp = controller.command_input_limits
        out = controller.command_output_limits
        if name == "base":
            np.testing.assert_allclose(array(inp), [[-1]*3, [1]*3])
            np.testing.assert_allclose(array(out), [[-.75, -.75, -1], [.75, .75, 1]])
            if controller.motor_type != "velocity" or controller.use_delta_commands:
                raise ValueError("Base command semantics changed")
        elif name.startswith("gripper"):
            if (controller._mode != "smooth" or controller._motor_type != "position"
                    or controller._inverted):
                raise ValueError("Unqualified gripper convention")
            np.testing.assert_allclose(array(inp).reshape(2), [-1, 1])
            gripper_ranges.append(array(out).reshape(2).tolist())
        else:
            if (controller.motor_type != "position" or controller.use_delta_commands
                    or inp is not None or out is not None):
                raise ValueError("Absolute joint hold semantics changed")
        controllers[name] = controller
        records[name] = {"type": typename, "indices": list(range(lo, hi)),
                         "input_limits": None if inp is None else array(inp).tolist(),
                         "output_limits": None if out is None else array(out).tolist()}
    # These vectors are inspected, never sent to a simulator or goal update.
    hold = np.asarray(base_hold(proprio, BodyTwist(0, 0, 0), gripper_ranges=gripper_ranges))
    np.testing.assert_allclose(hold, reference, atol=2e-5, rtol=0)
    rows = []
    for twist in (BodyTwist(0, 0, 0), BodyTwist(.03, 0, 0), BodyTwist(-.03, 0, 0),
                  BodyTwist(0, .03, 0), BodyTwist(0, -.03, 0), BodyTwist(0, 0, .05)):
        action = np.asarray(base_hold(proprio, twist, gripper_ranges=gripper_ranges))
        np.testing.assert_array_equal(action[3:], hold[3:])
        processed = {}
        for name, (lo, hi, _) in LAYOUT.items():
            raw = torch.from_numpy(action[lo:hi].astype(np.float32))
            value = array(cb.to_torch(controllers[name]._preprocess_command(cb.from_torch(raw))))
            if name == "base":
                expected = [twist.vx, twist.vy, twist.wz]
            elif name.startswith("gripper"):
                start = 24 if name.endswith("left") else 49
                expected = [float(np.mean(proprio[start:start+2]))]
            else:
                expected = hold[lo:hi]
            np.testing.assert_allclose(value, expected, atol=2e-5, rtol=0)
            processed[name] = value.tolist()
        rows.append({"raw_action": action.tolist(), "processed": processed})
    return {"codec_parity_passed": True, "hold_max_error": float(np.max(abs(hold-reference))),
            "settled_on_capture": settled(proprio), "controllers": records,
            "gripper_ranges": gripper_ranges, "unexecuted_probes": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--allow-simulator", required=True, action="store_true")
    parser.add_argument("--licenses-accepted", required=True, action="store_true")
    parser.add_argument("--hold-steps", type=int, default=0)
    parser.add_argument("--allow-motion", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.hold_steps <= 60 or (args.hold_steps and not args.allow_motion):
        parser.error("Hold diagnostic needs --allow-motion and at most 60 steps")
    source, output = args.source.resolve(), args.output.resolve()
    check_source(source, BEHAVIOR_COMMIT)
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise ValueError("Audit is restricted to simulator GPU 0")
    output.mkdir(parents=True, exist_ok=False)
    report = {"kind": "native-base-hold-codec-audit", "passed": False,
              "actions_sent": 0, "model_calls": 0, "motion_qualified": False,
              "source_revision": BEHAVIOR_COMMIT,
              "setup_physics": "ordinary evaluator reset/load only; not zero physics ticks",
              "remaining_gates": ["online full-robot swept clearance including unknown space",
                                  "measured native stop and settle", "online base localization"]}

    def save():
        (output / "audit.json").write_text(json.dumps(report, indent=2) + "\n")

    save()
    try:
        import omnigibson as og
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
            raise ValueError("Radio instance mismatch")
        with Evaluator(OmegaConf.create(config)) as evaluator:
            evaluator.reset()
            evaluator.load_task_instance(native_id)
            evaluator.reset()
            if not np.isclose(og.sim.get_sim_step_dt(), 1/30):
                raise ValueError("Native control timestep changed")
            store = EvidenceStore(output / "evidence")
            observation = BehaviorObservationFilter(store).convert(
                evaluator.obs, Stamp(session=str(uuid.uuid4()), epoch=0, sequence=0), time.monotonic())
            (output / "observation.json").write_text(observation.model_dump_json(indent=2) + "\n")
            report.update(inspect(evaluator.robot, observation.proprio), native_id=301)
            if args.hold_steps:
                def save_hold(state):
                    report["hold_diagnostic"] = state
                    report["actions_sent"] = state["actions_executed"]
                    save()
                result = stationary_hold(evaluator, observation, store, report["gripper_ranges"],
                                         args.hold_steps, save_hold)
                report["passed"] = result["settled"]
            else:
                report["passed"] = True
            save()  # Isaac shutdown may terminate Python before normal finalization.
    except BaseException as error:
        report.update(passed=False, error_type=type(error).__name__)
        save()
        raise


if __name__ == "__main__":
    main()
