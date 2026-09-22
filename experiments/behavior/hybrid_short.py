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
from contextlib import nullcontext
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


def execute_policy(transport, observation, store, step, capture, report, save, preprocessing,
                   *, action_budget=POLICY_ACTIONS, dense_capture=None):
    if action_budget not in (384, 768):
        raise ValueError("Only fixed short or separately labeled acquisition budgets are supported")
    if dense_capture is not None and action_budget != 768:
        raise ValueError("Dense capture requires the fixed extended acquisition")
    stamp = observation.stamp.model_dump()
    if transport.reset(stamp)["stamp"] != stamp:
        raise ValueError("Policy reset acknowledgement mismatch")
    started = time.monotonic()
    while report["policy_actions"] < action_budget:
        if time.monotonic() - started > 900:
            raise TimeoutError("Short policy exposure exceeded wall budget")
        stamp = observation.stamp.model_dump()
        before = time.monotonic()
        reply = transport.infer({"stamp": stamp, "instruction": INSTRUCTION,
            "proprio": observation.proprio,
            "rgb": {camera: store.read(ref) for camera, ref in observation.rgb.items()}})
        actions = selected_prefix(reply, stamp, min(32, action_budget - report["policy_actions"]), 32)
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
            count = report["policy_actions"]
            if dense_capture is not None and 384 <= count <= 512 and count % 4 == 0 and count % 32:
                dense_capture()
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


def execute_post_handoff(transport, observation, store, step, capture, report, save, preprocessing):
    """Equal fresh-reset exposure after the separately labeled exploratory intervention."""
    probe = report.get("exploratory_transit", {}).get("report", {})
    if (report.get("policy_actions") != 768 or report.get("native_end")
            or any(probe.get(k) is not True for k in
                   ("passed", "feedback_complete", "experimental_stop_observed"))
            or observation.stamp.sequence != report["native_actions"]):
        raise ValueError("Incomplete acquisition or exploratory stop; no policy handoff")
    if "post_handoff" in report:
        raise ValueError("Policy handoff is one-shot")
    post = {"native_actions": report["native_actions"], "policy_actions": 0,
            "policy_chunks": [], "policy_action_budget": POLICY_ACTIONS,
            "reset_sequence": observation.stamp.sequence, "completed": False,
            "handoff_observation": observation.model_dump()}
    report["post_handoff"] = post
    report["total_policy_actions"] = report["policy_actions"]

    def post_step(action):
        done = step(action)
        post["native_actions"] = report["native_actions"]
        return done

    def post_save():
        report["total_policy_actions"] = report["policy_actions"] + post["policy_actions"]
        save()

    final = execute_policy(transport, observation, store, post_step, capture,
                           post, post_save, preprocessing, action_budget=POLICY_ACTIONS)
    post["completed"] = post["policy_actions"] == POLICY_ACTIONS and not post.get("native_end")
    post_save()
    if not post["completed"]:
        raise RuntimeError("Post-handoff exposure censored; not a completed matched short trial")
    return final


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--condition", choices=("A", "B"), required=True)
    parser.add_argument("--policy-load-receipt", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8011)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--grounding-port", type=int,
                        help="Optional synchronous target-grounding shadow, never motion authority")
    parser.add_argument("--extended-grounding-acquisition", action="store_true",
                        help="Separate 768-action policy-only acquisition, not A-short")
    parser.add_argument("--dense-observation-diagnostic", action="store_true",
                        help="Shadow RGB-D every 4 actions at 384..512; no extra model calls")
    parser.add_argument("--feedback-hold-diagnostic", action="store_true",
                        help="Separate robot-only substep feedback during 60 zero-base holds")
    parser.add_argument("--exploratory-transit", action="store_true",
                        help="One approved simulator-only target-directed probe, unknown clearance")
    parser.add_argument("--matched-target-handoff", action="store_true",
                        help="Same acquisition, A zero holds/B exploratory transit, then 384 policy actions")
    parser.add_argument("--robot-assets", type=Path,
                        help="Pinned robot-only FK assets for the exploratory transit")
    parser.add_argument("--assisted-target-probe", action="store_true",
                        help="Separate paused-world single-yaw diagnostic after policy exposure")
    for flag in ("allow-simulator", "allow-unknown-clearance-exploration", "licenses-accepted"):
        parser.add_argument("--" + flag, action="store_true", required=True)
    args = parser.parse_args()
    if args.grounding_port and ((args.condition != "A" and not args.matched_target_handoff)
                               or args.assisted_target_probe):
        parser.error("Grounding shadow is isolated to policy-only A captures")
    if args.extended_grounding_acquisition and not args.grounding_port:
        parser.error("Extended acquisition requires synchronous grounding shadow")
    if args.feedback_hold_diagnostic and (
            args.condition != "A" or args.grounding_port or args.assisted_target_probe):
        parser.error("Feedback hold requires isolated A exposure without grounding or assisted probe")
    if args.exploratory_transit and (
            args.condition != "A" or not args.grounding_port or not args.robot_assets
            or not args.extended_grounding_acquisition or args.feedback_hold_diagnostic
            or args.assisted_target_probe):
        parser.error("Exploratory transit requires isolated extended A grounding and robot assets")
    if args.matched_target_handoff and (
            not args.grounding_port or not args.robot_assets or not args.extended_grounding_acquisition
            or args.exploratory_transit or args.feedback_hold_diagnostic or args.assisted_target_probe):
        parser.error("Matched handoff requires extended grounding/robot assets and no other diagnostic")
    target_experiment = args.exploratory_transit or args.matched_target_handoff
    if args.dense_observation_diagnostic and (
            args.condition != "A" or not args.extended_grounding_acquisition
            or target_experiment or args.feedback_hold_diagnostic or args.assisted_target_probe):
        parser.error("Dense observations require isolated extended policy-only A")
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
    report["seed"] = args.seed
    if args.grounding_port:
        report["scope"] = "online_target_grounding_shadow_during_frozen_policy_approach"
    if args.extended_grounding_acquisition:
        report["scope"] = "extended_online_target_acquisition_not_a_short_comparison"
    if args.feedback_hold_diagnostic:
        report["scope"] = "policy_approach_then_zero_base_feedback_not_handoff_qualification"
    if args.exploratory_transit:
        report["scope"] = "one_target_directed_10cm_exploratory_probe_not_benchmark_admission"
    if args.matched_target_handoff:
        report["scope"] = "matched_acquisition_exploratory_target_handoff_not_strict_benchmark"
        report["post_handoff_policy_budget"] = POLICY_ACTIONS
        report["total_policy_action_ceiling"] = 768 + POLICY_ACTIONS
    report["policy_action_budget"] = 768 if args.extended_grounding_acquisition else POLICY_ACTIONS
    report["policy_action_ceiling"] = report["policy_action_budget"]
    if args.dense_observation_diagnostic:
        report["dense_observation_diagnostic"] = {
            "start": 384, "end": 512, "stride": 4, "captures": [],
            "boundary_captures_reused": True, "motion_authority": False,
            "policy_inputs_unchanged": True, "additional_model_calls": 0,
        }

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
        seed_everything(args.seed)
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
                if args.grounding_port:
                    from .target_grounding import ground_capture

                    row["target_grounding"] = ground_capture(
                        row, store, HttpPolicyTransport(args.grounding_port, timeout_s=30),
                        output / "grounding_masks")
                    if target_experiment:
                        row["target_grounding"]["delivery"] = "synchronous_before_next_native_action"
                        row["target_grounding"]["usage"] = "exploratory_target_evidence_not_strict_admission"
                    save()
                return observation

            def step(action):
                hook.action = action
                terminated, truncated = evaluator.step()
                report["native_actions"] += 1
                save()
                return bool(terminated or truncated)

            def dense_capture():
                current = stamp.model_copy(update={"sequence": report["native_actions"]})
                observation = ingress.convert(evaluator.obs, current, time.monotonic())
                row = capture_record(evaluator, observation)
                report["dense_observation_diagnostic"]["captures"].append(row)
                save()

            evaluator.start_recording(str(output / "rollout.mp4"))
            observation = capture(track=args.condition == "B" and not args.matched_target_handoff)
            report["codec"] = inspect(evaluator.robot, observation.proprio)
            if args.condition == "B" and not args.matched_target_handoff:
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
            policy_feedback = None
            if args.feedback_hold_diagnostic:
                from .feedback_diagnostic import FeedbackDiagnostic

                policy_feedback = FeedbackDiagnostic(og.sim, evaluator.robot, source_revision=BEHAVIOR_COMMIT)

            def policy_step(action):
                if policy_feedback is not None:
                    policy_feedback.mark(control_sequence=report["native_actions"] + 1, phase="policy_motion")
                return step(action)

            try:
                with policy_feedback if policy_feedback is not None else nullcontext():
                    final = execute_policy(HttpPolicyTransport(args.port), observation, store, policy_step, capture,
                        report, save, lambda actions: verify_native_preprocessing(evaluator.robot, actions),
                        action_budget=report["policy_action_budget"],
                        dense_capture=dense_capture if args.dense_observation_diagnostic else None)
            finally:
                if policy_feedback is not None:
                    packet = json.loads(policy_feedback.to_json())
                    (output / "policy_feedback.json").write_text(json.dumps(packet, indent=2) + "\n")
                    report["policy_feedback"] = {k: v for k, v in packet.items() if k != "rows"}
                    save()
            if policy_feedback is not None and (
                    packet["error"] or packet["truncated"] or not packet["callback_removed"]
                    or len(packet["rows"]) != 4 * report["policy_actions"]):
                raise RuntimeError("Policy-motion feedback capture incomplete")
            if args.feedback_hold_diagnostic:
                from .feedback_diagnostic import run_feedback_hold

                def save_feedback(packet):
                    (output / "feedback.json").write_text(json.dumps(packet, indent=2) + "\n")
                    report["feedback_hold"] = packet["report"]
                    save()

                final, feedback_report = run_feedback_hold(
                    sim=og.sim, robot=evaluator.robot, initial=final,
                    gripper_ranges=report["codec"]["gripper_ranges"], step=step,
                    capture=capture, save_feedback=save_feedback, source_revision=BEHAVIOR_COMMIT)
                if not feedback_report["feedback_complete"]:
                    raise RuntimeError("Substep feedback diagnostic incomplete: " + str(feedback_report["error"]))
            if args.assisted_target_probe:
                from .assisted_probe import run_assisted_probe

                report["scope"] = "policy_approach_then_assisted_target_probe_not_ab_comparison"

                def save_probe(state):
                    report["assisted_probe"] = state
                    save()

                final = run_assisted_probe(final, store, report["codec"]["gripper_ranges"],
                                           step, capture, output, save_probe)
            if target_experiment:
                from .exploratory_transit import run_exploratory_transit

                if report.get("native_end"):
                    raise RuntimeError("Episode ended before exploratory transit")
                report["probe_code_sha256"] = {
                    name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                    for name in ("exploratory_transit.py", "base_hold.py", "feedback_diagnostic.py",
                                 "head_depth_shadow.py", "target_grounding.py", "grounding_manifest.py")}
                save()

                def save_transit(state):
                    report["exploratory_transit"] = state
                    save()

                final = run_exploratory_transit(
                    final, sim=og.sim, robot=evaluator.robot, store=store,
                    gripper_ranges=report["codec"]["gripper_ranges"], step=step,
                    capture=capture, latest_row=lambda: report["captures"][-1],
                    output=output, save_probe=save_transit, robot_assets=args.robot_assets,
                    control_only=args.matched_target_handoff and args.condition == "A")
                if args.matched_target_handoff:
                    final = execute_post_handoff(
                        HttpPolicyTransport(args.port), final, store, step, capture, report, save,
                        lambda actions: verify_native_preprocessing(evaluator.robot, actions))
            evaluator.stop_recording()
            probe_ok = not target_experiment or report["exploratory_transit"]["report"]["passed"]
            report.update(passed=bool(probe_ok), data_collection_completed=True,
                          final_observation=final.model_dump(),
                          native_success_evaluation_only=bool(evaluator.env.task.success))
            save()
    except BaseException as error:
        report.update(passed=False, error_type=type(error).__name__, error=str(error))
        save()
        raise


if __name__ == "__main__":
    main()
