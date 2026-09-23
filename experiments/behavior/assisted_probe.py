"""Paused-world assisted yaw diagnostic, never autonomous navigation admission."""

import json
import time

import numpy as np

from experiments.behavior.base_hold import base_hold, settled
from physical_harness.execution.handoff.classical import BodyTwist


def validate_selection(selection, observation, store):
    if (selection.get("stamp") != observation.stamp.model_dump()
            or selection.get("rgb_evidence_id") != observation.rgb["head"].id
            or selection.get("depth_evidence_id") != observation.depth["head"].id):
        raise ValueError("Assisted selection is not bound to the current observation")
    if selection.get("decision") == "not_visible":
        return None
    if (selection.get("decision") != "yaw" or type(selection.get("direction")) is not int
            or selection["direction"] not in (-1, 1)):
        raise ValueError("Only one bounded assisted yaw or no-motion refusal is allowed")
    pixel = selection.get("pixel_uv")
    if not isinstance(pixel, list) or len(pixel) != 2 or any(type(v) is not int for v in pixel):
        raise ValueError("Expected integer target pixel")
    depth = store.read(observation.depth["head"])
    u, v = pixel
    if not (2 <= u < depth.shape[1]-2 and 2 <= v < depth.shape[0]-2):
        raise ValueError("Target pixel outside interior depth image")
    patch = depth[v-2:v+3, u-2:u+3]
    if not np.isfinite(patch).all() or np.any(patch <= 0) or np.any(patch > 10):
        raise ValueError("Target pixel has no valid measured depth neighborhood")
    return {"direction": selection["direction"], "pixel_uv": pixel,
            "depth_m": float(depth[v, u]), "depth_range_m": [float(patch.min()), float(patch.max())]}


def run_assisted_probe(initial, store, gripper_ranges, step, capture, output, save):
    """One 15-tick yaw after strict settling; at most 60 hold ticks per stop.

    The simulator is explicitly paused for an external visual annotation. This
    diagnostic neither runs the strict hybrid freshness gate nor bypasses it.
    It reports paused wall time and cannot qualify an autonomous handoff.
    """
    anchor = np.asarray(initial.proprio)
    indices = [*range(3, 10), *range(28, 35), *range(53, 57)]
    hold = base_hold(anchor, BodyTwist(0, 0, 0), gripper_ranges=gripper_ranges)
    report = {"scope": "assisted_paused_world_single_yaw", "passed": False,
              "autonomous": False, "motion_qualified": False, "clearance": "unknown",
              "strict_gates_overridden": False, "actions": 0, "samples": [],
              "stop_acknowledged": False, "gpt_api_calls": 0}

    def tick(command, phase, emergency=False):
        ended = step(command)
        report["actions"] += 1
        save(report)
        if ended:
            raise RuntimeError("Native episode ended during assisted probe")
        obs = capture()
        p = np.asarray(obs.proprio)
        drift = float(np.max(np.abs(p[indices] - anchor[indices])))
        grip_drift = float(np.max(np.abs(p[[24, 25, 49, 50]]-anchor[[24, 25, 49, 50]])))
        stopped = settled(p) and np.linalg.norm(p[:2]) <= .002 and abs(p[2]) <= .005
        report["samples"].append({"stamp": obs.stamp.model_dump(), "phase": phase,
            "joint_drift": drift, "gripper_drift_m": grip_drift,
            "stopped": bool(stopped), "native_action": list(command)})
        save(report)
        if not emergency and (drift > .03 or grip_drift > .006
                              or np.linalg.norm(p[:2]) > .08 or abs(p[2]) > .15):
            raise RuntimeError("Assisted probe exceeded drift/speed limits")
        return obs, stopped

    def brake(phase, emergency=False):
        report["stop_acknowledged"] = False
        consecutive = 0
        for _ in range(60):
            obs, stopped = tick(hold, phase, emergency)
            consecutive = consecutive + 1 if stopped else 0
            if consecutive == 5:
                report["stop_acknowledged"] = True
                save(report)
                return obs
        raise RuntimeError("Assisted probe failed measured stopping within 60 ticks")

    try:
        frozen = brake("initial_settling")
        request = {"observation": frozen.model_dump(), "scope": report["scope"],
                   "allowed": ["not_visible", "one_15_tick_yaw_at_0.05_rad_per_s"],
                   "state": "simulator_paused_no_steps_until_selection"}
        (output / "selection_request.json").write_text(json.dumps(request, indent=2) + "\n")
        response = output / "selection_response.json"
        started = time.monotonic()
        while not response.exists():
            if time.monotonic() - started > 300:
                raise TimeoutError("No assisted target selection within five minutes")
            time.sleep(.2)
        selection = json.loads(response.read_text())
        report["paused_wall_s"] = time.monotonic() - started
        report["selection"] = selection
        target = validate_selection(selection, frozen, store)
        if target is None:
            report["outcome"] = "target_not_visible_no_yaw"
            save(report)
            return frozen
        report["target"] = target
        report["stop_acknowledged"] = False
        save(report)
        command = base_hold(anchor, BodyTwist(0, 0, .05 * target["direction"]),
                            gripper_ranges=gripper_ranges)
        for _ in range(15):
            tick(command, "assisted_yaw")
        final = brake("final_braking")
        report.update(passed=True, outcome="pulse_and_measured_stop_completed")
        save(report)
        return final
    except BaseException as error:
        report["error"] = type(error).__name__ + ": " + str(error)
        if not report["stop_acknowledged"]:
            try:
                brake("emergency_hold", emergency=True)
            except BaseException as stop_error:
                report["stop_error"] = str(stop_error)
        save(report)
        raise
