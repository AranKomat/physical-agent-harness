"""Bounded empty-scene response diagnostic, not a benchmark motion controller."""

import numpy as np

from physical_harness.hybrid_v0.classical import BodyTwist

from .base_hold import base_hold, settled

PULSES = (("forward", .03, 0., 0.), ("backward", -.03, 0., 0.),
          ("left", 0., .03, 0.), ("right", 0., -.03, 0.),
          ("yaw_positive", 0., 0., .05), ("yaw_negative", 0., 0., -.05))


def run_pulses(initial, step, gripper_ranges, save, *, characterize_unsettled=False,
               pulse_names=None):
    """Fixed 15-tick pulses with <=60 braking ticks each, at 30 Hz.

    step sends exactly one native action and returns legal proprio[61]. The
    caller must provide an explicitly authorized simulator calibration fixture
    or labeled unknown-clearance exploration. Nothing here supplies a collision
    predicate or hybrid admission. actions_executed counts successful callbacks;
    native callers must separately journal steps completed before capture errors.
    Explicit characterization may measure response despite failed stop checks,
    but can NEVER return passed=True and retains the same drift/speed aborts.
    """
    names = tuple(p[0] for p in PULSES) if pulse_names is None else tuple(pulse_names)
    if not names or len(names) != len(set(names)) or any(n not in {p[0] for p in PULSES} for n in names):
        raise ValueError("Choose unique named calibration pulses")
    pulses = [p for p in PULSES if p[0] in names]
    initial = np.asarray(initial, dtype=float)
    hold = base_hold(initial, BodyTwist(0, 0, 0), gripper_ranges=gripper_ranges)
    indices = [*range(3, 10), *range(28, 35), *range(53, 57)]
    report = {"actions_attempted": 0, "actions_executed": 0, "passed": False,
              "motion_qualified": False, "benchmark_result": False, "samples": [],
              "pulses": [], "stop_acknowledged": False,
              "characterization_only": characterize_unsettled, "stop_failures": [],
              "pulse_names": [p[0] for p in pulses]}

    def tick(command, phase, *, enforce_drift=True):
        report["actions_attempted"] += 1
        save(report)
        p = np.asarray(step(command), dtype=float)
        report["actions_executed"] += 1
        save(report)
        if p.shape != (61,) or not np.isfinite(p).all():
            raise ValueError("Invalid proprioception after native action")
        drift = float(np.max(np.abs(p[indices] - initial[indices])))
        grip_drift = float(np.max(np.abs(p[[24, 25, 49, 50]] - initial[[24, 25, 49, 50]])))
        stopped = settled(p) and np.linalg.norm(p[:2]) <= .002 and abs(p[2]) <= .005
        row = {"sequence": report["actions_executed"], "phase": phase,
               "native_action": list(command), "proprio": p.tolist(),
               "joint_drift": drift, "gripper_drift_m": grip_drift,
               "stopped": bool(stopped), "control_time_s": report["actions_executed"] / 30}
        report["samples"].append(row)
        save(report)
        if enforce_drift and (drift > .03 or grip_drift > .006
                              or np.linalg.norm(p[:2]) > .08 or abs(p[2]) > .15):
            raise RuntimeError("Empty-scene response exceeded diagnostic abort limits")
        return p, row

    def brake(phase, *, emergency=False):
        consecutive, rows = 0, []
        report["stop_acknowledged"] = False
        for _ in range(60):
            _, row = tick(hold, phase, enforce_drift=not emergency)
            rows.append(row)
            consecutive = consecutive + 1 if row["stopped"] else 0
            if consecutive == 5:
                report["stop_acknowledged"] = True
                save(report)
                return rows
        report["stop_failures"].append(phase)
        save(report)
        if characterize_unsettled and not emergency:
            return rows
        raise RuntimeError("No measured stop within 60 hold ticks")

    try:
        brake("initial_settling")
        for name, vx, vy, wz in pulses:
            report["stop_acknowledged"] = False
            command = base_hold(initial, BodyTwist(vx, vy, wz), gripper_ranges=gripper_ranges)
            moving = [tick(command, name)[0] for _ in range(15)]
            braking = brake(name + ":braking")
            mean = np.mean(np.asarray(moving[-5:])[:, :3], axis=0)
            target = np.array([vx, vy, wz])
            axis = int(np.flatnonzero(target)[0])
            tolerance = abs(target[axis]) * .2 + (.003 if axis < 2 else .005)
            tracking = abs(mean[axis] - target[axis]) <= tolerance
            cross = all(abs(mean[j]) <= (.005 if j < 2 else .01) for j in range(3) if j != axis)
            # Integrate sampled speeds, not positions; disclose this as a proxy.
            speeds = np.array([moving[-1][:3], *[r["proprio"][:3] for r in braking]])
            path = np.linalg.norm(speeds[:, :2], axis=1)
            yaw = np.abs(speeds[:, 2])
            report["pulses"].append({"name": name, "command_twist": target.tolist(),
                "last_five_mean_twist": mean.tolist(), "response_passed": bool(tracking and cross),
                "braking_ticks": len(braking), "stop_acknowledged": report["stop_acknowledged"],
                "acknowledgement_s": len(braking) / 30 if report["stop_acknowledged"] else None,
                "settled_suffix_start_s": (len(braking) - 4) / 30 if report["stop_acknowledged"] else None,
                "braking_translation_proxy_m": float(np.sum((path[:-1] + path[1:]) / 60)),
                "braking_yaw_proxy_rad": float(np.sum((yaw[:-1] + yaw[1:]) / 60))})
            save(report)
            if (not tracking or not cross) and not characterize_unsettled:
                raise RuntimeError("Base response does not follow command within diagnostic limits")
        report["characterization_completed"] = characterize_unsettled
        report["passed"] = not characterize_unsettled
        save(report)
        return report
    except BaseException as error:
        report["error_type"] = type(error).__name__
        report["error"] = str(error)
        save(report)
        if not report["stop_acknowledged"]:
            try:
                brake("emergency_hold", emergency=True)
            except BaseException as stop_error:
                report["stop_error"] = type(stop_error).__name__ + ": " + str(stop_error)
        save(report)
        raise
