"""Read-only robot feedback at physics-substep boundaries; never stop authority.

Audited BEHAVIOR b1979916ec1549b10a4e65e630bc6504a9af1b00 sources,
relative to OmniGibson/omnigibson:
  simulator.py:471-475 dynamically dispatches _on_post_physics_step;
  simulator.py:1444-1472 refreshes backend views before returning;
  prims/entity_prim.py:846-895 exposes native position/velocity getters.

Use only in a separately labeled, single-owner synchronous diagnostic after
simulator initialization/warmup. The caller must verify the actual checkout;
source_revision is an explicit attestation, not a runtime source hash check.
The logger imports no simulator/Torch and performs no actions or disk I/O.
The separate run_feedback_hold helper calls only caller-supplied step/capture/save
functions for its explicitly bounded zero-base diagnostic; it is not a gate bypass.
Wrapping the existing handler adds read/copy overhead, not a physics subscription.
Same-callback reads are not proof of atomic native getter timestamps.

Example (caller owns all stepping and any output-file writing)::

    with FeedbackDiagnostic(sim, robot, source_revision=PINNED_REVISION) as log:
        log.mark(control_sequence=384, phase="zero_base_hold")
        # Caller performs its separately authorized diagnostic here.
    detached_json = log.to_json()

The 2000-row cap counts physics callbacks, not control actions. No wraparound or
subsampling hides overflow; inspect rows_dropped and error before using results.
Base virtual positions, scene state, poses, cameras and task truth are excluded.
"""

from __future__ import annotations

import json
import math
import threading
import time

import numpy as np

from physical_harness.hybrid_v0.classical import BodyTwist

from .base_hold import base_hold, settled
from .contracts import Observation

PINNED_REVISION = "b1979916ec1549b10a4e65e630bc6504a9af1b00"
JOINT_NAMES = (
    *(f"{side}_arm_joint{i}" for side in ("left", "right") for i in range(1, 8)),
    *(f"torso_joint{i}" for i in range(1, 5)),
    *(f"{side}_gripper_finger_joint{i}" for side in ("left", "right") for i in (1, 2)),
)
_HOOK = "_on_post_physics_step"


def _finite(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Nonfinite feedback/time")
    return result


def _selected(value, indices):
    # Select before copying so virtual base coordinates never enter stored rows.
    selected = value[list(indices)]
    if hasattr(selected, "detach"):
        selected = selected.detach().clone().cpu()
    values = selected.tolist()
    if len(values) != len(indices):
        raise ValueError("Joint feedback shape changed")
    return [_finite(v) for v in values]


class FeedbackDiagnostic:
    """One-shot context manager; export a detached JSON snapshot with to_json().

    Install, mark, export, and remove on the synchronous simulation-owner thread,
    outside stepping. A preexisting instance hook is rejected rather than stacked.
    Diagnostic read failures disable sampling, not physics; original callback
    exceptions still propagate. Cleanup never overwrites another owner's hook.
    """

    def __init__(self, sim, robot, *, source_revision, max_rows=2000,
                 clock=time.monotonic):
        if source_revision != PINNED_REVISION:
            raise ValueError("Unreviewed BEHAVIOR revision")
        if type(max_rows) is not int or not 1 <= max_rows <= 2000:
            raise ValueError("max_rows must be an integer in [1, 2000]")
        if not callable(clock):
            raise ValueError("clock must be callable")
        self._sim, self._robot, self._clock = sim, robot, clock
        self._max_rows = max_rows
        self._rows = []
        self._indices = ()
        self._owner = threading.get_ident()
        self._used = self._active = self._removed = False
        self._seen = self._dropped = 0
        self._error = None
        self._phase, self._sequence = "unlabeled", None
        self._last_stamp = None
        self._wrapper = None

    def _owner_idle(self):
        if threading.get_ident() != self._owner:
            raise RuntimeError("Diagnostic requires the simulation-owner thread")
        if (self._sim.currently_stepping is not False
                or self._sim.currently_in_isaac_step is not False
                or self._sim._in_sim_lifecycle != 0):
            raise RuntimeError("Diagnostic lifecycle operation during simulation step")

    def __enter__(self):
        self._owner_idle()
        if self._used:
            raise RuntimeError("Diagnostic context is one-shot")
        if _HOOK in vars(self._sim):
            raise RuntimeError("Existing instance post-physics hook; refusing to replace")
        original = getattr(self._sim, _HOOK)
        if not callable(original) or self._sim._post_physics_step_callback is None:
            raise RuntimeError("Pinned post-physics subscription unavailable")
        if not all(callable(getattr(self._robot, name, None)) for name in
                   ("get_joint_positions", "get_joint_velocities")):
            raise ValueError("Native robot feedback getters required")
        indices = []
        for name in JOINT_NAMES:
            dofs = self._robot.joints[name].dof_indices
            if len(dofs) != 1:
                raise ValueError("Expected one DOF per named R1Pro joint")
            index = int(dofs[0])
            if index < 0 or index >= self._robot.n_dof or index in indices:
                raise ValueError("Invalid/duplicate robot DOF mapping")
            indices.append(index)
        self._indices = tuple(indices)
        self._physics_dt = _finite(self._sim.get_physics_dt())
        if self._physics_dt <= 0:
            raise ValueError("Positive physics dt required")
        self._start = _finite(self._clock())

        def wrapped(*args, **kwargs):
            try:
                result = original(*args, **kwargs)
            except BaseException as exc:
                self._error = "original_callback_failed:" + type(exc).__name__
                raise
            if self._active:
                self._capture()
            return result

        self._wrapper = wrapped
        setattr(self._sim, _HOOK, wrapped)
        self._active = self._used = True
        return self

    def mark(self, *, control_sequence, phase):
        """Attach caller-supplied action boundary labels; never read policy state."""
        self._owner_idle()
        if not self._active:
            raise RuntimeError("Diagnostic not installed")
        if type(control_sequence) is not int or control_sequence < 0:
            raise ValueError("Nonnegative integer control sequence required")
        if not isinstance(phase, str) or not phase.strip() or len(phase) > 80:
            raise ValueError("Short nonempty diagnostic phase required")
        self._sequence, self._phase = control_sequence, phase

    def _stamp(self):
        index = self._sim.current_time_step_index
        if type(index) is not int or index < 0:
            raise ValueError("Invalid native physics step counter")
        return index, _finite(self._sim.current_time)

    def _capture(self):
        self._seen += 1
        if self._error is not None or len(self._rows) >= self._max_rows:
            self._dropped += 1
            return
        try:
            if threading.get_ident() != self._owner:
                raise RuntimeError("Callback is not on the simulation-owner thread")
            if self._sim.currently_stepping or self._sim.currently_in_isaac_step:
                raise RuntimeError("Original post-physics callback did not finish")
            before = self._stamp()
            if self._last_stamp is not None and (
                before[0] <= self._last_stamp[0] or before[1] <= self._last_stamp[1]
            ):
                raise ValueError("Physics clock/counter did not advance")
            q = _selected(self._robot.get_joint_positions(), self._indices)
            v = _selected(self._robot.get_joint_velocities(), self._indices)
            if self._stamp() != before:
                raise RuntimeError("Physics stamp changed between feedback reads")
            elapsed = _finite(self._clock()) - self._start
            if elapsed < 0:
                raise ValueError("Wall clock regressed")
            self._rows.append({
                "callback_index": self._seen, "physics_step_index": before[0],
                "sim_time_s": before[1], "wall_elapsed_s": elapsed,
                "control_sequence": self._sequence, "phase": self._phase,
                "joint_positions": q, "native_joint_velocities": v,
            })
            self._last_stamp = before
        except Exception as exc:
            self._error = "feedback_read_failed:" + type(exc).__name__
            self._dropped += 1

    def close(self):
        """Remove only our wrapper. Safe to call again after successful cleanup."""
        self._owner_idle()
        if not self._active:
            return
        self._active = False
        if vars(self._sim).get(_HOOK) is not self._wrapper:
            self._error = "cleanup_hook_ownership_conflict"
            raise RuntimeError("Post-physics hook changed; not overwriting another owner")
        delattr(self._sim, _HOOK)
        self._removed = True

    def __exit__(self, exc_type, exc, traceback):
        try:
            self.close()
        except Exception as cleanup_error:
            if exc is None:
                raise
            exc.add_note(f"Feedback diagnostic cleanup failed: {type(cleanup_error).__name__}")
        return False

    def to_json(self):
        """Return detached JSON; no file write and no simulator/robot references."""
        self._owner_idle()
        return json.dumps({
            "schema_version": 1,
            "scope": "robot_only_physics_feedback_diagnostic_not_stop_qualification",
            "source_revision_attested": PINNED_REVISION,
            "motion_qualified": False, "actions_sent_by_logger": 0,
            "native_getter_atomicity_proven": False,
            "joint_names": JOINT_NAMES, "dof_indices": self._indices,
            "position_units": ["rad"] * 18 + ["m"] * 4,
            "velocity_units": ["rad/s"] * 18 + ["m/s"] * 4,
            "physics_dt_s": getattr(self, "_physics_dt", None),
            "max_rows": self._max_rows, "callbacks_seen": self._seen,
            "rows_dropped": self._dropped,
            "truncated": self._dropped > 0, "error": self._error,
            "installed": self._active, "callback_removed": self._removed,
            "rows": self._rows,
        }, allow_nan=False, indent=2)


def run_feedback_hold(*, sim, robot, initial, gripper_ranges, step, capture,
                      save_feedback, source_revision=PINNED_REVISION):
    """Run at most 60 constant zero-base holds, logging physics substeps only here.

    Caller owns prior policy exposure and attests the pinned source/runtime. This
    must be a separately authorized, empty-handed diagnostic, not navigation or
    an admission override. Initial settling is deliberately not required.

    step(command) returns a bool indicating episode termination; capture() returns
    the next Observation with sequence +1, same episode and a newer timestamp.
    No retries, emergency actions, yaw, transit, policy calls or gate changes occur.
    Even if stopped early, all 60 holds run unless a guard/error aborts the helper.

    Returns (last_valid_observation, report). Runtime/setup failures are reported
    with passed=False; interruptions propagate after export. save_feedback(packet)
    is always attempted once in finally, after logger cleanup. The detached packet
    contains report and feedback dictionaries. Save failures propagate to the caller
    rather than returning a claimed success. A failed step has an uncertain action
    outcome; actions_attempted and actions_completed are counted separately.
    """
    final = initial
    log = None
    report = {
        "scope": "post_policy_zero_base_feedback_hold_diagnostic",
        "passed": False, "motion_qualified": False, "benchmark_result": False,
        "strict_gates_overridden": False, "hold_limit": 60,
        "actions_attempted": 0, "actions_completed": 0,
        "samples": [], "final_consecutive_stopped": 0,
        "stop_acknowledged": False, "error": None, "logger_error": None,
        "feedback_complete": False,
    }
    try:
        if not isinstance(initial, Observation):
            raise ValueError("Initial Observation required")
        if not all(callable(fn) for fn in (step, capture, save_feedback)):
            raise ValueError("Step, capture and feedback-save callbacks required")
        anchor = np.asarray(initial.proprio, dtype=float)
        joints = [*range(3, 10), *range(28, 35), *range(53, 57)]
        fingers = [24, 25, 49, 50]
        command = base_hold(anchor, BodyTwist(0, 0, 0), gripper_ranges=gripper_ranges)
        report["native_hold_command"] = list(command)
        # An entry-speed gate would prevent observing braking from policy motion.
        # Zero-base holds still enforce every original post-step speed/drift bound.
        log = FeedbackDiagnostic(sim, robot, source_revision=source_revision, max_rows=2000)
        with log:
            for _ in range(60):
                sequence = final.stamp.sequence + 1
                log.mark(control_sequence=sequence, phase="post_policy_zero_base_hold")
                seen = log._seen
                report["actions_attempted"] += 1
                ended = step(command)
                report["actions_completed"] += 1
                if type(ended) is not bool:
                    raise ValueError("Step must return a bool episode-ended flag")
                if ended:
                    raise RuntimeError("Episode ended during feedback hold")
                obs = capture()
                if (not isinstance(obs, Observation)
                        or not obs.stamp.same_episode(final.stamp)
                        or obs.stamp.sequence != sequence
                        or obs.observed_at <= final.observed_at):
                    raise ValueError("Feedback hold requires a fresh next-sequence observation")
                p = np.asarray(obs.proprio, dtype=float)
                is_settled = settled(p)
                speed, yaw = float(np.linalg.norm(p[:2])), float(abs(p[2]))
                drift = float(np.max(np.abs(p[joints] - anchor[joints])))
                grip_drift = float(np.max(np.abs(p[fingers] - anchor[fingers])))
                stopped = bool(is_settled and speed <= .002 and yaw <= .005)
                final = obs
                report["final_consecutive_stopped"] = (
                    report["final_consecutive_stopped"] + 1 if stopped else 0
                )
                report["samples"].append({
                    "stamp": obs.stamp.model_dump(), "observed_at": obs.observed_at,
                    "settled": bool(is_settled), "stopped": stopped,
                    "base_linear_speed_m_s": speed, "base_abs_yaw_rate_rad_s": yaw,
                    "joint_drift_rad": drift, "finger_drift_m": grip_drift,
                })
                if drift > .03 or grip_drift > .006 or speed > .08 or yaw > .15:
                    raise RuntimeError("Feedback hold exceeded diagnostic drift/speed guard")
                if log._error is not None or log._dropped:
                    raise RuntimeError("Feedback logger failed or truncated during hold")
                if log._seen == seen:
                    raise RuntimeError("No physics feedback callbacks during hold")
        report["stop_acknowledged"] = report["final_consecutive_stopped"] >= 5
        if not report["stop_acknowledged"]:
            report["error"] = "Final five-consecutive measured stop not established"
    except BaseException as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        if not isinstance(exc, Exception):
            raise
    finally:
        feedback = None
        if log is not None:
            try:
                feedback = json.loads(log.to_json())
                report["logger_error"] = feedback["error"]
                report["feedback_complete"] = bool(
                    feedback["callback_removed"] and not feedback["installed"]
                    and not feedback["error"] and not feedback["truncated"]
                    and len(report["samples"]) == 60
                    and {r["control_sequence"] for r in feedback["rows"]}
                    == {s["stamp"]["sequence"] for s in report["samples"]}
                )
            except Exception as exc:
                report["logger_error"] = f"feedback_export_failed:{type(exc).__name__}"
        report["passed"] = bool(
            report["error"] is None and report["feedback_complete"]
            and report["stop_acknowledged"] and report["actions_completed"] == 60
        )
        # Serialization detaches report as well: a save callback cannot mutate the return value.
        save_feedback(json.loads(json.dumps({"report": report, "feedback": feedback},
                                            allow_nan=False)))
    return final, report
