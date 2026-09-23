"""Separate control duty, inference use, wall latency, and device energy.

Fewer policy-controlled timesteps are NOT a measured reduction in GPU energy.
All counters derive from receipts
missing/invalid receipts remain visible.
"""
from __future__ import annotations

from dataclasses import dataclass

from physical_harness.core.actions import integer, number, text


def summarize(journal, *, control_dt: float = 1/30) -> dict:
    dt = number(control_dt, low=.000001)
    starts, receipts, terminals = {}, {}, {}
    reservations = set()
    for p in journal.records("compiled_action"):
        key = (p["attempt_id"], p.get("step_index"))
        if p["event"] == "reserved":
            reservations.add(p["attempt_id"])
        elif p["event"] == "step_started":
            starts[key] = p
        elif p["event"] == "step_receipt":
            if key in receipts:
                raise ValueError("Duplicate receipt in metrics")
            receipts[key] = p
        elif p["event"] == "terminal":
            terminals[p["attempt_id"]] = p
    if receipts.keys()-starts.keys():
        raise ValueError("Receipt without phase reservation")
    steps = learned = dof_steps = total_dof_steps = calls = 0
    execution_wall = inference_known_s = 0.
    inference_unknown = False
    for key, p in receipts.items():
        r, start = p["receipt"], starts[key]
        n = integer(r["native_steps"])
        dofs = integer(start["robot_dofs"], low=1, high=256)
        policy_dofs = integer(r["policy_dofs"], high=dofs)
        steps += n
        calls += integer(r["policy_calls"])
        total_dof_steps += n*dofs
        execution_wall += number(p["wall_s"], low=0)
        if p["primitive"] == "frozen_policy":
            learned += n
            dof_steps += n*policy_dofs
            if r.get("policy_inference_s") is None:
                inference_unknown = True
            else:
                inference_known_s += number(r["policy_inference_s"], low=0)
    unresolved = len(starts.keys()-receipts.keys())
    model_calls = {}
    model_wall = {}
    for p in journal.records("compiled_model_usage"):
        role = p["role"]
        model_calls[role] = model_calls.get(role, 0)+integer(p["calls"])
        model_wall[role] = model_wall.get(role, 0)+number(p["wall_s"], low=0)
    return {"known_robot_steps": steps, "known_policy_steps": learned,
            "known_classical_steps": steps-learned,
            "known_robot_sim_s": steps*dt, "known_policy_sim_s": learned*dt,
            "policy_action_time_fraction": learned/steps if steps else None,
            "policy_dof_time_fraction": dof_steps/total_dof_steps if total_dof_steps else None,
            "known_policy_dof_seconds": dof_steps*dt, "policy_inference_calls": calls,
            "known_execution_wall_s": execution_wall,
            "policy_inference_s": None if inference_unknown else inference_known_s,
            "unresolved_steps": unresolved,
            "unclosed_attempts": len(reservations-terminals.keys()),
            "complete_action_accounting": (unresolved == 0 and not reservations-terminals.keys()
                                           and not any(p.get("fault_latched") for p in terminals.values())),
            "unresolved_stop_attempts": sum(p["stop_acknowledged"] is not True for p in terminals.values()),
            "auxiliary_model_calls_by_role": model_calls, "auxiliary_model_wall_s_by_role": model_wall,
            "energy_joules": None, "semantic_success": "not_inferred_from_motion",
            "scope": "validated-receipts-only; fractions are partial when accounting is incomplete"}


def record_model_usage(journal, *, call_id: str, role: str, calls: int, wall_s: float):
    text(call_id)
    if role not in {"executive", "verifier", "grasp_generation", "perception", "captioner"}:
        raise ValueError("Use motor receipts for policy calls to avoid double counting")
    integer(calls, low=0)
    number(wall_s, low=0)
    journal.put("compiled_model_usage", call_id, {"role": role, "calls": calls, "wall_s": wall_s})


@dataclass(frozen=True)
class PowerSample:
    device: str
    wall_time: float
    watts: float

    def __post_init__(self):
        text(self.device)
        number(self.wall_time, low=0)
        number(self.watts, low=0, high=100000)


def integrate_device_energy(samples: tuple[PowerSample, ...], *, max_gap_s: float = 1) -> dict:
    """Trapezoidal device energy across the sampled window, not model attribution.

    No idle subtraction or multi-process allocation is inferred. Each device is
    integrated once
    callers compare matched windows and report sampling gaps.
    """
    number(max_gap_s, low=.000001)
    by_device = {}
    for s in samples:
        if not isinstance(s, PowerSample):
            raise ValueError("Typed power sample required")
        by_device.setdefault(s.device, []).append(s)
    out = {}
    for device, rows in by_device.items():
        if len(rows) < 2:
            raise ValueError("At least two samples per device required")
        joules = 0.
        for a, b in zip(rows, rows[1:]):
            gap = b.wall_time-a.wall_time
            if not 0 < gap <= max_gap_s:
                raise ValueError("Nonmonotonic power samples or unmeasured gap")
            joules += (a.watts+b.watts)*.5*gap
        out[device] = {"joules": joules, "window_s": rows[-1].wall_time-rows[0].wall_time,
                       "attribution": "whole-device; includes other workloads and idle"}
    return out
