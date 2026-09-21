"""Compile parameterized intent into bounded controller programs, not actions.

All programs still need robot-specific IK, full swept collision (including the
payload), native codec, and online monitor approval. These templates do not
contain an R1Pro actuator implementation or force sensor assumption.
"""
from __future__ import annotations

from dataclasses import dataclass

from .types import Gripper, Primitive, Program, Proposal, Step, Verb, integer, number, text, unit


@dataclass(frozen=True)
class TemplateConfig:
    step_cap: int = 120
    policy_steps: int = 384
    contact_step_cap: int = 600
    approach_m: float = .05
    lift_m: float = .03
    press_limit_m: float = .02
    pull_limit_m: float = .10
    transit_speed_m_s: float = .03
    contact_speed_m_s: float = .005
    robot_dofs: int = 23
    # No implicit local-map +Z/gravity equivalence. Calibrate this direction.
    up_direction: tuple[float, float, float] | None = None
    up_evidence_id: str | None = None

    def __post_init__(self):
        integer(self.step_cap, low=1, high=10000)
        integer(self.policy_steps, low=1, high=100000)
        integer(self.contact_step_cap, low=1, high=10000)
        integer(self.robot_dofs, low=1, high=256)
        for value in (self.approach_m, self.lift_m, self.press_limit_m, self.pull_limit_m):
            number(value, low=.00001, high=.5)
        number(self.transit_speed_m_s, low=.00001, high=.5)
        number(self.contact_speed_m_s, low=.00001, high=.05)
        if self.up_direction is not None:
            unit(self.up_direction)
            text(self.up_evidence_id, "gravity/up calibration evidence")
        elif self.up_evidence_id is not None:
            raise ValueError("Up evidence without direction")


def compile_program(proposal: Proposal, gripper: Gripper,
                    config: TemplateConfig) -> Program:
    if proposal.gripper_fingerprint != gripper.fingerprint:
        raise PermissionError("Gripper embodiment mismatch")
    p, verb = proposal.parameters, proposal.intent.verb
    allowed_constraints = {"keep_upright", "avoid_rim", "use_left_arm", "use_right_arm", "no_base_motion"}
    constraints = set(proposal.intent.constraints)
    if not constraints <= allowed_constraints:
        raise ValueError("Unsupported semantic constraint; do not silently drop it")
    if {"use_left_arm", "use_right_arm"} <= constraints or (
        verb == Verb.NAVIGATE and "no_base_motion" in constraints
    ):
        raise ValueError("Contradictory action constraints")
    if p.opening_m is not None and p.opening_m > gripper.max_opening_m:
        raise ValueError("Requested opening exceeds actual gripper geometry")
    common = ("sensor_lineage", "target_grounded", "robot_model", "native_codec", "stop_monitor")
    metric = common+("known_space", "swept_collision", "joint_limits", "payload_geometry")
    arm = metric+("ik", "gripper_compatibility")
    def move(pose):
        return Step(Primitive.MOVE_EEF, pose, max_steps=config.step_cap,
                    max_speed_m_s=config.transit_speed_m_s)
    def passive(kind):
        return Step(kind, max_steps=0)
    if verb == Verb.INSPECT:
        steps, checks = (passive(Primitive.INSPECT),), ("sensor_lineage", "passive_capture")
    elif verb == Verb.NAVIGATE:
        steps = (Step(Primitive.MOVE_BASE, p.pose, max_steps=config.step_cap,
                      max_speed_m_s=config.transit_speed_m_s),)
        checks = metric+("localization", "base_response", "footprint")
    elif verb in {Verb.STAGE, Verb.RETRACT}:
        steps, checks = (move(p.pose),), arm
        if verb == Verb.RETRACT:
            checks += ("safe_release_or_stable_payload",)
    elif verb == Verb.GRASP:
        if config.up_direction is None:
            raise ValueError("Grasp/lift requires calibrated up direction, not guessed map +Z")
        pre = p.pose.shifted(p.pose.approach, -p.standoff_m)
        steps = (Step(Primitive.OPEN, opening_m=p.opening_m, max_steps=config.step_cap),
                 move(pre), move(p.pose),
                 Step(Primitive.CLOSE, max_steps=config.step_cap),
                 passive(Primitive.HOLD_CHECK),
                 move(p.pose.shifted(config.up_direction, config.lift_m)))
        checks = arm+("semantic_contact_region", "grasp_monitor", "up_calibration")
    elif verb == Verb.PLACE:
        if config.up_direction is None:
            raise ValueError("Place requires calibrated up direction")
        pre = p.pose.shifted(config.up_direction, p.standoff_m)
        steps = (passive(Primitive.HOLD_CHECK), move(pre), move(p.pose),
                 Step(Primitive.OPEN, opening_m=p.opening_m, max_steps=config.step_cap),
                 passive(Primitive.RELEASE_CHECK), move(pre))
        checks = arm+("held_attachment", "support_region", "release_monitor", "up_calibration")
    elif verb == Verb.PRESS:
        if not 0 < p.travel_m <= config.press_limit_m:
            raise ValueError("Press travel exceeds configured local envelope")
        # direction points INTO surface. Geometry owns this sign.
        pre = p.pose.shifted(p.direction, -p.standoff_m)
        end = p.pose.shifted(p.direction, p.travel_m)
        steps = (move(pre), Step(Primitive.PRESS, p.pose, end, max_steps=config.contact_step_cap,
                                max_speed_m_s=config.contact_speed_m_s),
                 passive(Primitive.RELEASE_CHECK), move(pre))
        checks = arm+("semantic_contact_region", "contact_normal", "contact_monitor",
                      "bounded_contact", "release_monitor")
    elif verb == Verb.PULL:
        if not 0 < p.travel_m <= config.pull_limit_m:
            raise ValueError("Pull travel exceeds configured local envelope")
        pre = p.pose.shifted(p.pose.approach, -p.standoff_m)
        end = p.pose.shifted(p.direction, p.travel_m)
        steps = (Step(Primitive.OPEN, opening_m=p.opening_m, max_steps=config.step_cap),
                 move(pre), move(p.pose), Step(Primitive.CLOSE, max_steps=config.step_cap),
                 passive(Primitive.HOLD_CHECK),
                 Step(Primitive.PULL, p.pose, end, max_steps=config.contact_step_cap,
                      max_speed_m_s=config.contact_speed_m_s))
        # A prismatic pull is NOT a generic door-open primitive.
        checks = arm+("semantic_contact_region", "linear_articulation_axis", "grasp_monitor",
                      "contact_monitor", "bounded_contact")
    elif verb == Verb.POLICY:
        steps = (Step(Primitive.POLICY, max_steps=config.policy_steps,
                      max_policy_calls=config.policy_steps, max_policy_chunks=config.policy_steps),)
        checks = common+("policy_identity", "policy_recipe", "policy_handoff")
    else:
        raise ValueError("Unsupported verb")
    checks += tuple("constraint_"+name for name in sorted(constraints))
    return Program(proposal, steps, tuple(dict.fromkeys(checks)), config.robot_dofs,
                   "parameterized-primitives-v1")
