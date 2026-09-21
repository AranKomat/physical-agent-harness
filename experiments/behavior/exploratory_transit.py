"""One explicitly authorized simulator probe; unknown clearance, NOT a strict gate.

Caller attests the pinned simulator/codec and owns synchronous capture/grounding.
Deadlines are cooperative: an outer watchdog must bound blocking native/RPC calls.
No world poses, obstacle clearance claims, recovery move, or policy handoff.
"""

import hashlib
import io
import json
import time
from pathlib import Path

import numpy as np

from physical_harness.hybrid_v0.classical import BodyTwist

from .base_hold import base_hold, settled
from .contracts import Observation
from .feedback_diagnostic import PINNED_REVISION, FeedbackDiagnostic
from .grounding_manifest import validate_online_identity
from .head_depth_shadow import point_to_plane
from .target_grounding import RobotSelfCheck, read_grounding_packet, validate_packet

CONTROL_DT = 1 / 30
WORK_WALL_S = 600.
BRAKE_WALL_S = 180.
CAPTURE_TO_COMMAND_S = 10.
MAX_ACTIONS = 260  # 60 prehold + 80 move + 60 final hold + 60 abort brake.
JOINTS = [*range(3, 10), *range(28, 35), *range(53, 57)]
FINGERS = [24, 25, 49, 50]


def _rigid(value):
    t = np.asarray(value, dtype=float)
    if (t.shape != (4, 4) or not np.isfinite(t).all()
            or not np.allclose(t[3], [0, 0, 0, 1], atol=1e-8)
            or not np.allclose(t[:3, :3].T @ t[:3, :3], np.eye(3), atol=1e-5)
            or not np.isclose(np.linalg.det(t[:3, :3]), 1, atol=1e-5)):
        raise ValueError("Invalid rigid transform")
    return t


def _frame(obs, row, store, fk):
    if Observation.model_validate(row["observation"]) != obs:
        raise ValueError("Latest row does not bind captured observation")
    packet = read_grounding_packet(row, store)
    _, k, _, depth = validate_packet(packet)
    return {"obs": obs, "k": k, "depth": depth, "extrinsic": _rigid(fk.transform(obs))}


def _target(frame, row, output):
    obs, depth, k = frame["obs"], frame["depth"], frame["k"]
    g = row["target_grounding"]
    validate_online_identity(g.get("identity"))
    if (g.get("stamp") != obs.stamp.model_dump()
            or g.get("rgb_evidence_id") != obs.rgb["head"].id
            or g.get("depth_evidence_id") != obs.depth["head"].id
            or g.get("motion_authorized") is not False
            or g.get("delivery") != "synchronous_before_next_native_action"
            or g.get("omitted_target_count") != 0):
        raise ValueError("Stale, truncated or non-synchronous grounding")
    accepted = [c for c in g["candidates"] if not c.get("rejected")]
    if len(accepted) != 1 or accepted[0]["label"] not in ("radio", "a radio"):
        raise ValueError("Target lost or ambiguous")
    candidate = accepted[0]
    ref = candidate["derived_mask"]
    root = (Path(output) / "grounding_masks").resolve()
    path = (root / ref["uri"]).resolve()
    if (path.parent != root or path.name != ref["uri"] or path.suffix != ".npy"
            or ref["stamp"] != g["stamp"] or ref["rgb_evidence_id"] != g["rgb_evidence_id"]):
        raise ValueError("Detached target mask")
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != ref["sha256"] or path.stem != ref["sha256"]:
        raise ValueError("Target mask content mismatch")
    mask = np.load(io.BytesIO(content), allow_pickle=False)
    if mask.dtype != bool or mask.shape != depth.shape:
        raise ValueError("Invalid target mask")
    valid = mask & np.isfinite(depth) & (depth > 0) & (depth <= 10)
    if mask.sum() < 16 or valid.sum() < 16 or valid.sum() / mask.sum() < .8:
        raise ValueError("Insufficient target depth")
    v, u = np.nonzero(valid)
    indices = np.linspace(0, len(u)-1, min(len(u), 4096), dtype=int)
    v, u = v[indices], u[indices]
    z = depth[v, u]
    camera = np.median(np.column_stack(((u-k[0, 2])*z/k[0, 0],
                                       (v-k[1, 2])*z/k[1, 1], z)), axis=0)
    point = (frame["extrinsic"] @ np.r_[camera, 1.])[:3]
    if (not np.allclose(camera, candidate["surface_median_camera_m"], atol=1e-6)
            or not np.allclose(point, candidate["surface_median_base_m"], atol=1e-6)
            or min(np.linalg.norm(point-np.asarray(obs.proprio)[i:i+3]) for i in (17, 42)) < .18
            or np.linalg.norm(point[:2]) < .10):
        raise ValueError("Target geometry mismatch or near-hand/near-base ambiguity")
    return point


def _pair(previous, current):
    if not np.array_equal(previous["k"], current["k"]):
        raise ValueError("Pair calibration changed")
    k = current["k"]
    h, w = current["depth"].shape
    ok, delta, _ = point_to_plane(None, previous["depth"], None, current["depth"],
                                 dict(width=w, height=h, fx=k[0, 0], fy=k[1, 1],
                                      cx=k[0, 2], cy=k[1, 2]))
    if not ok:
        raise ValueError("Adjacent depth fit rejected; base motion unknown")
    local = _rigid(previous["extrinsic"] @ np.linalg.inv(_rigid(delta))
                   @ np.linalg.inv(current["extrinsic"]))
    distance = float(np.linalg.norm(local[:3, 3]))
    yaw = float(np.arctan2(local[1, 0], local[0, 0]))
    return local, {"translation_m": distance, "yaw_rad": yaw,
                   "rotation_rad": float(np.arccos(np.clip((np.trace(local[:3, :3])-1)/2, -1, 1))),
                   "translation_rate_m_s": distance / CONTROL_DT,
                   "abs_yaw_rate_rad_s": abs(yaw) / CONTROL_DT}


def _joint_window(log, phase):
    if log._error or log._dropped:
        raise ValueError("Physics logger failed or truncated")
    rows = log._rows[-21:]
    if len(rows) < 21 or any(r["phase"] != phase for r in rows):
        return None
    q = np.asarray([r["joint_positions"] for r in rows])
    dt = np.diff([r["sim_time_s"] for r in rows])
    if (q.shape != (21, 22) or not np.isfinite(q).all()
            or not np.allclose(dt, 1/120, rtol=0, atol=1e-8)
            or any(b["physics_step_index"] != a["physics_step_index"] + 1
                   for a, b in zip(rows, rows[1:]))):
        raise ValueError("Invalid trailing physics intervals")
    rates = np.abs(np.diff(q, axis=0)) / dt[:, None]
    return {"joint_max_rad_s": float(rates[:, :18].max()),
            "finger_max_m_s": float(rates[:, 18:].max())}


def run_exploratory_transit(initial, *, sim, robot, store, gripper_ranges, step,
                            capture, latest_row, output, save_probe, robot_assets):
    """Return last fresh observation; save detached {report, feedback} after cleanup.

    At 30 Hz, command integral <=8 cm; measured adjacent endpoint path triggers
    braking at 8 cm and hard-abort status at 10 cm (not a physical guarantee).
    Aborts never resume motion. Brake failures are retained, not treated as stops.
    """
    started = time.monotonic()
    final, frame, target, log, zero = initial, None, None, None, None
    pairs = []
    tracking_lost = False
    episode_ended = False
    sequence = initial.stamp.sequence
    sequence_known = True
    context_installed = False
    integrated = np.eye(4)
    report = dict(scope="simulator_only_experimental_unknown_clearance_probe",
                  passed=False, clearance="unknown", strict_gate_passed=False,
                  motion_qualified=False, stop_certified=False, error=None,
                  actions_attempted=0, actions_completed=0, commanded_integral_m=0.,
                  native_calls_attempted=0,
                  commands=[],
                  measured_path_m=0., measured_path_complete=True, hard_abort=False,
                  drive_rotation_path_rad=0., drive_rotation_limit_rad=.05,
                  brake_attempts=0, experimental_stop_observed=False, samples=[],
                  brake_errors=[], wall_budget_s=WORK_WALL_S + BRAKE_WALL_S,
                  capture_to_command_budget_s=CAPTURE_TO_COMMAND_S,
                  action_budget=MAX_ACTIONS, callback_deadlines_cooperative=True)

    def progress(phase):
        try:
            save_probe(json.loads(json.dumps({"report": report, "feedback": None}, allow_nan=False)))
        except Exception as exc:
            if phase != "abort_brake":
                raise
            report["brake_errors"].append(f"progress_save:{type(exc).__name__}: {exc}")

    def observe(phase, *, reobserve=False):
        nonlocal final, frame, target, tracking_lost, integrated
        native_before = sim.current_time_step_index
        obs = capture()
        if (not isinstance(obs, Observation) or not obs.stamp.same_episode(final.stamp)
                or not sequence_known or obs.stamp.sequence != sequence
                or obs.observed_at <= final.observed_at
                or sim.current_time_step_index != native_before):
            raise ValueError("Expected fresh same-episode synchronous observation")
        final = obs
        if tracking_lost:
            raise ValueError("Tracking lost; fresh capture retained but no estimator retry")
        row = latest_row()
        current = _frame(obs, row, store, fk)
        sample = {"phase": phase, "stamp": obs.stamp.model_dump(),
                  "rgb_evidence_id": obs.rgb["head"].id,
                  "depth_evidence_id": obs.depth["head"].id}
        sample["raw_proprio_settled"] = bool(settled(obs.proprio))
        report["samples"].append(sample)
        if not reobserve:
            try:
                local, pair = _pair(frame, current)
            except BaseException:
                tracking_lost = True
                report["measured_path_complete"] = False
                raise
            sample.update(pair)
            sample["previous_base_from_current"] = local.tolist()
            integrated = _rigid(integrated @ local)
            report["entry_base_from_current"] = integrated.tolist()
            pairs.append({**pair, "phase": phase})
            report["measured_path_m"] += pair["translation_m"]
            if target is not None:
                target = (np.linalg.inv(local) @ np.r_[target, 1.])[:3]
        frame = current
        if report["measured_path_m"] >= .10:
            report["hard_abort"] = True
            raise ValueError("Measured path reached 10 cm hard abort")
        p = np.asarray(obs.proprio)
        if (np.max(np.abs(p[JOINTS]-anchor[JOINTS])) > .03
                or np.max(np.abs(p[FINGERS]-anchor[FINGERS])) > .006
                or (phase != "entry" and (np.linalg.norm(p[:2]) > .08 or abs(p[2]) > .15))):
            raise ValueError("Joint drift or proprio speed guard")
        if phase != "abort_brake":
            fresh_target = _target(current, row, output)
            if target is not None and np.linalg.norm(fresh_target-target) > .10:
                raise ValueError("Target continuity drift")
            target = fresh_target
            sample["surface_median_base_m"] = target.tolist()
        if phase == "move":
            report["drive_rotation_path_rad"] += sample["rotation_rad"]
            if (sample["translation_rate_m_s"] > .08
                    or sample["abs_yaw_rate_rad_s"] > .15
                    or sample["rotation_rad"] / CONTROL_DT > .15
                    or report["drive_rotation_path_rad"] > .05):
                raise ValueError("Drive depth/FK rate/rotation guard")
        window = _joint_window(log, phase)
        sample["joint_window"] = window
        recent = pairs[-5:]
        return bool(window and window["joint_max_rad_s"] <= .03
                    and window["finger_max_m_s"] <= .005 and len(recent) == 5
                    and all(r["phase"] == phase and r["translation_rate_m_s"] <= .002
                            and r["abs_yaw_rate_rad_s"] <= .005 for r in recent))

    def act(command, phase, deadline):
        nonlocal episode_ended, tracking_lost, sequence, sequence_known
        if time.monotonic() >= deadline or report["actions_attempted"] >= MAX_ACTIONS:
            raise TimeoutError("Exploratory action/wall budget exhausted")
        if episode_ended:
            raise RuntimeError("Episode already ended")
        if phase == "move":
            latency = time.monotonic() - final.observed_at
            report["capture_to_command_latency_s"] = latency
            if not 0 <= latency <= CAPTURE_TO_COMMAND_S:
                raise TimeoutError("Fresh target exceeded capture-to-command wall budget")
        before = len(log._rows) if log is not None else 0
        if log is not None and log._active and sequence_known:
            try:
                log.mark(control_sequence=sequence + 1, phase=phase)
            except Exception:
                if phase != "abort_brake":
                    raise
        native_before = sim.current_time_step_index
        record = {"phase": phase, "command": list(command), "pre_sequence": sequence if sequence_known else None,
                  "post_sequence": None, "native_physics_before": native_before, "completed": False}
        record["capture_to_command_latency_s"] = time.monotonic() - final.observed_at
        report["commands"].append(record)
        report["actions_attempted"] += 1
        if phase == "move":
            report["commanded_integral_m"] += float(np.linalg.norm(command[:2])) * .75 * CONTROL_DT
        progress(phase)
        latency = time.monotonic() - final.observed_at
        if (time.monotonic() >= deadline
                or (phase == "move" and not 0 <= latency <= CAPTURE_TO_COMMAND_S)):
            record["dispatch_cancelled"] = "pre-step persistence exceeded freshness/wall budget"
            if phase == "move":
                report["commanded_integral_m"] -= float(np.linalg.norm(command[:2])) * .75 * CONTROL_DT
            raise TimeoutError(record["dispatch_cancelled"])
        report["native_calls_attempted"] += 1
        try:
            ended = step(command)
        except BaseException as exc:
            record["step_error"] = f"{type(exc).__name__}: {exc}"
            record["native_physics_after"] = sim.current_time_step_index
            tracking_lost = True
            sequence_known = False
            report["measured_path_complete"] = False
            if log is not None:
                log.close()  # An uncertain action outcome cannot be given a fabricated sequence.
            raise
        sequence += 1
        record.update(completed=True, post_sequence=sequence if sequence_known else None,
                      native_physics_after=sim.current_time_step_index)
        report["actions_completed"] += 1
        episode_ended = ended is True
        progress(phase)
        if type(ended) is not bool or episode_ended:
            report["measured_path_complete"] = False
            raise RuntimeError("Episode ended or invalid step result")
        if phase == "abort_brake" and tracking_lost:
            record["blind_zero_only"] = True
            return False
        old_frame = frame
        try:
            stopped = observe(phase)
        except BaseException as exc:
            record["observation_error"] = f"{type(exc).__name__}: {exc}"
            if frame is old_frame:
                tracking_lost = True
                report["measured_path_complete"] = False
            raise
        rows = log._rows[before:]
        if (len(rows) != 4 or not np.isclose(log._physics_dt, 1/120)
                or sim.current_time_step_index != native_before + 4
                or any(r["physics_step_index"] != native_before + i + 1
                       or r["control_sequence"] != final.stamp.sequence
                       for i, r in enumerate(rows))):
            raise ValueError("Expected four pinned physics substeps per action")
        if time.monotonic() >= deadline:
            raise TimeoutError("Exploratory wall budget exhausted")
        return stopped

    try:
        anchor = np.asarray(initial.proprio, dtype=float)
        zero = base_hold(anchor, BodyTwist(0, 0, 0), gripper_ranges=gripper_ranges)
        fk = RobotSelfCheck(Path(robot_assets))
        log = FeedbackDiagnostic(sim, robot, source_revision=PINNED_REVISION, max_rows=2000)
        log.__enter__()
        context_installed = True
        # Reobserve before prehold; no old remembered target is used for entry.
        observe("entry", reobserve=True)
        deadline = started + WORK_WALL_S
        for _ in range(60):
            if act(zero, "prehold", deadline):
                break
        else:
            raise RuntimeError("Experimental prehold stop not observed within 60 actions")
        report["prehold_experimental_stop"] = True
        direction = target[:2] / np.linalg.norm(target[:2])
        report["direction_base_xy"] = direction.tolist()
        command = base_hold(anchor, BodyTwist(float(.03*direction[0]), float(.03*direction[1]), 0),
                            gripper_ranges=gripper_ranges)
        for _ in range(80):
            if report["measured_path_m"] >= .08:
                break
            if report["commanded_integral_m"] + .03*CONTROL_DT > .08 + 1e-12:
                break
            act(command, "move", deadline)
        for _ in range(60):
            if act(zero, "final_hold", deadline):
                break
        else:
            raise RuntimeError("Experimental final stop not observed within 60 actions")
        observe("final_hold", reobserve=True)
        if time.monotonic() >= deadline:
            raise TimeoutError("Final reobservation exceeded wall budget")
        report["experimental_stop_observed"] = True
        report["passed"] = True
    except BaseException as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        report["passed"] = False
        # Reserve a separate bounded brake interval, even after tracking/step errors.
        deadline = min(time.monotonic() + BRAKE_WALL_S,
                       started + WORK_WALL_S + BRAKE_WALL_S)
        can_brake = (zero is not None and context_installed
                     and report["native_calls_attempted"] > 0 and not episode_ended)
        if not isinstance(exc, Exception) or not sequence_known:
            # Interruptions/uncertain native steps get one zero, never more native retries.
            report["native_sequence_uncertain"] = not sequence_known
            report["measured_path_complete"] = False
            if can_brake:
                record = {"phase": "interrupt_brake", "command": list(zero),
                          "pre_sequence": sequence if sequence_known else None,
                          "post_sequence": None, "completed": False,
                          "native_physics_before": sim.current_time_step_index}
                report["commands"].append(record)
                report["actions_attempted"] += 1
                report["brake_attempts"] += 1
                try:
                    progress("abort_brake")
                    if log is not None:
                        log.close()
                    report["native_calls_attempted"] += 1
                    ended = step(zero)
                    record.update(completed=True, post_sequence=sequence+1 if sequence_known else None,
                                  native_physics_after=sim.current_time_step_index)
                    report["actions_completed"] += 1
                    episode_ended = ended is True
                except BaseException as brake_error:
                    record["step_error"] = f"{type(brake_error).__name__}: {brake_error}"
                progress("abort_brake")
            if not isinstance(exc, Exception):
                raise
        elif can_brake:
            for _ in range(60):
                if (episode_ended or time.monotonic() >= deadline
                        or report["actions_attempted"] >= MAX_ACTIONS):
                    break
                report["brake_attempts"] += 1
                try:
                    if act(zero, "abort_brake", deadline):
                        report["experimental_stop_observed"] = True
                        break
                except BaseException as brake_error:
                    report["brake_errors"].append(f"{type(brake_error).__name__}: {brake_error}")
                    if not isinstance(brake_error, Exception):
                        raise
                    if not sequence_known:
                        break  # No repeated stepping of a simulator with uncertain outcome.
            if not episode_ended and time.monotonic() < deadline:
                try:
                    observe("abort_brake", reobserve=True)
                except BaseException as observe_error:
                    report["brake_errors"].append(f"final_reobserve:{type(observe_error).__name__}: {observe_error}")
    finally:
        feedback = None
        if log is not None:
            try:
                log.close()
            except Exception as exc:
                report["passed"] = False
                report["cleanup_error"] = f"{type(exc).__name__}: {exc}"
            try:
                feedback = json.loads(log.to_json())
            except Exception as exc:
                report["passed"] = False
                report["export_error"] = f"{type(exc).__name__}: {exc}"
        report["wall_elapsed_s"] = time.monotonic() - started
        report["feedback_complete"] = bool(
            feedback and feedback.get("callback_removed") and not feedback.get("installed")
            and not feedback.get("error") and not feedback.get("truncated")
            and feedback.get("rows_dropped") == 0
            and len(feedback.get("rows", [])) == 4 * report["actions_completed"])
        if not report["feedback_complete"]:
            report["passed"] = False
        report["episode_ended"] = episode_ended
        report["final_stamp"] = final.stamp.model_dump()
        save_probe(json.loads(json.dumps({"report": report, "feedback": feedback}, allow_nan=False)))
    return final
