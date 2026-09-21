"""Pure offline joint-only stop shadow; never a control or base-stop gate.

evaluate_joint_stop_shadow accepts the FeedbackDiagnostic dictionary itself, not
the enclosing {report, feedback} packet. It requires a cleaned-up, untruncated
packet of complete four-substep control groups at 120 Hz, all in one phase. Gaps
or mixed phases refuse the whole packet; independent packets never share history.

Each ready result uses the trailing 20 consecutive position differences, ending
at that row. The first 20 rows are not_ready. No interpolation, endpoint averaging,
angle unwrapping, padding, future samples or relaxed velocity limits are used.
native_joint_stationary compares the *ending row's* instantaneous native joint
velocities with the same limits, not a finite-difference or base-speed estimate.

Timing tolerances cover floating-point clocks only, never stopping thresholds.
Finite differences are interval averages and cannot prove absence of sub-interval
motion, getter/solver timing differences, base motion, or safe motion authority.
"""

import math
from collections import deque

PINNED_REVISION = "b1979916ec1549b10a4e65e630bc6504a9af1b00"
JOINT_NAMES = (
    *(f"{side}_arm_joint{i}" for side in ("left", "right") for i in range(1, 8)),
    *(f"torso_joint{i}" for i in range(1, 5)),
    *(f"{side}_gripper_finger_joint{i}" for side in ("left", "right") for i in (1, 2)),
)
_PHASES = ("policy_motion", "post_policy_zero_base_hold")
_UNITS = ["rad"] * 18 + ["m"] * 4


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _finite(value):
    _require(type(value) in (int, float), "Expected finite numeric feedback/time")
    _require(math.isfinite(value), "Nonfinite feedback/time")
    return float(value)


def _counter(value):
    _require(type(value) is int and value >= 0, "Invalid counter")
    return value


def _rates(values):
    return {"joints_rad_s": max(abs(v) for v in values[:18]),
            "fingers_m_s": max(abs(v) for v in values[18:])}


def _stationary(rates):
    return rates["joints_rad_s"] <= .03 and rates["fingers_m_s"] <= .005


def evaluate_joint_stop_shadow(feedback):
    """Return detached per-row windows or explicit refusal; do not mutate input.

    At most 2000 rows are accepted. Valid complete-packet extensions cannot alter
    previously emitted windows. Packet-integrity failures instead refuse all rows;
    do not interpret a refused packet as a causal measurement of stationary joints.
    Source revision is checked as declared metadata, not authenticated provenance.
    """
    result = {
        "schema_version": 1, "scope": "offline_joint_only_position_stop_shadow",
        "status": "not_ready", "reason": None, "motion_authorized": False,
        "base_stop_evaluated": False, "native_provenance_verified": False,
        "window_intervals": 20, "physics_per_control": 4,
        "joint_limit_rad_s": .03, "finger_limit_m_s": .005,
        "native_comparison": "instantaneous native velocities at window-ending row",
        "windows": [],
    }
    try:
        _require(isinstance(feedback, dict), "Expected FeedbackDiagnostic dictionary")
        _require(type(feedback.get("schema_version")) is int
                 and feedback["schema_version"] == 1, "Unsupported schema")
        _require(feedback.get("source_revision_attested") == PINNED_REVISION,
                 "Unreviewed source revision")
        _require(feedback.get("joint_names") == list(JOINT_NAMES),
                 "Expected exact ordered 22 named joints")
        indices = feedback.get("dof_indices")
        _require(isinstance(indices, list) and len(indices) == 22
                 and all(type(i) is int and i >= 0 for i in indices)
                 and len(set(indices)) == 22, "Invalid declared DOF mapping")
        _require(feedback.get("position_units") == _UNITS
                 and feedback.get("velocity_units") == [u + "/s" for u in _UNITS],
                 "Named-joint units mismatch")
        _require("error" in feedback and feedback["error"] is None, "Logger error or missing status")
        _require(type(feedback.get("rows_dropped")) is int and feedback["rows_dropped"] == 0
                 and feedback.get("truncated") is False, "Dropped/truncated feedback")
        _require(feedback.get("callback_removed") is True and feedback.get("installed") is False,
                 "Logger cleanup not complete")
        dt = _finite(feedback.get("physics_dt_s"))
        _require(dt > 0 and math.isclose(dt, 1 / 120, rel_tol=1e-6, abs_tol=1e-12),
                 "Expected positive 120 Hz physics dt")
        rows = feedback.get("rows")
        _require(isinstance(rows, list) and len(rows) <= 2000, "Invalid or oversized row list")
        capacity = feedback.get("max_rows")
        _require(type(capacity) is int and 1 <= capacity <= 2000 and len(rows) <= capacity,
                 "Invalid logger capacity")
        _require(type(feedback.get("callbacks_seen")) is int
                 and feedback["callbacks_seen"] == len(rows), "Callback count mismatch")
        _require(len(rows) % 4 == 0, "Incomplete four-physics-step control group")
        parsed = []
        for i, row in enumerate(rows):
            _require(isinstance(row, dict), f"Invalid row {i}")
            callback = _counter(row.get("callback_index"))
            physics = _counter(row.get("physics_step_index"))
            sequence = _counter(row.get("control_sequence"))
            sim_time = _finite(row.get("sim_time_s"))
            wall_time = _finite(row.get("wall_elapsed_s"))
            _require(sim_time >= 0 and wall_time >= 0, f"Negative time at row {i}")
            phase = row.get("phase")
            _require(phase in _PHASES, f"Unsupported phase at row {i}")
            vectors = []
            for name in ("joint_positions", "native_joint_velocities"):
                values = row.get(name)
                _require(isinstance(values, list) and len(values) == 22, f"Invalid {name} shape")
                vectors.append(tuple(_finite(v) for v in values))
            if i:
                previous = parsed[-1]
                _require(callback == previous["callback"] + 1
                         and physics == previous["physics"] + 1, f"Counter gap/stale row {i}")
                elapsed = sim_time - previous["sim_time"]
                _require(elapsed > 0 and math.isclose(elapsed, dt, rel_tol=1e-5, abs_tol=1e-9),
                         f"Physics sim-time gap/stale row {i}")
                _require(wall_time >= previous["wall_time"], f"Regressed wall time at row {i}")
                _require(phase == parsed[0]["phase"], "Mixed phases require separate packets")
                _require(sequence == parsed[0]["sequence"] + i // 4,
                         f"Not four consecutive physics rows per control step at row {i}")
            parsed.append({"callback": callback, "physics": physics, "sequence": sequence,
                           "sim_time": sim_time, "wall_time": wall_time, "phase": phase,
                           "q": vectors[0], "v": vectors[1]})
        history = deque(maxlen=20)
        windows = []
        for i, row in enumerate(parsed):
            if i:
                rates = tuple(abs(a - b) / dt for a, b in zip(row["q"], parsed[i - 1]["q"]))
                _require(all(math.isfinite(v) for v in rates), "Nonfinite derived rate")
                history.append(_rates(rates))
            ready = len(history) == 20
            max_rates = {key: max(r[key] for r in history) for key in
                         ("joints_rad_s", "fingers_m_s")} if ready else None
            native = _rates(row["v"])
            windows.append({
                "callback_index": row["callback"], "physics_step_index": row["physics"],
                "sim_time_s": row["sim_time"], "control_sequence": row["sequence"],
                "phase": row["phase"], "status": "ready" if ready else "not_ready",
                "interval_count": len(history), "max_rates": max_rates,
                "joint_stationary_candidate": _stationary(max_rates) if ready else None,
                "native_max_rates": native, "native_joint_stationary": _stationary(native),
                "motion_authorized": False,
            })
        result["windows"] = windows
        result["status"] = "evaluated" if len(parsed) >= 21 else "not_ready"
    except (ValueError, TypeError, OverflowError) as exc:
        result.update(status="refused", reason=str(exc), windows=[])
    return result
