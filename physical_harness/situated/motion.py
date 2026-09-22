"""Bounded model-authored keyposes -> existing reviewed Program/Catalog.

This is an ADDITIONAL proposal interface, not a weakening of select_action.
Model replies cannot supply qualification, speed, force, budget, frame transforms,
absolute joint actions, or executable Python. Direct contact is not implemented:
use existing guarded press/pull/grasp primitives instead.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

from ..action_compiler.primitives import TemplateConfig, compile_program
from ..action_compiler.types import (
    Basis,
    Gripper,
    Intent,
    Parameters,
    Pose,
    Primitive,
    Program,
    Proposal,
    Step,
    Verb,
    digest,
    encode,
    ids,
    integer,
    number,
    strict_loads,
    text,
    vector,
)


@dataclass(frozen=True)
class PoseAnchor:
    id: str
    basis: Basis
    entity: str
    pose: Pose
    evidence_ids: tuple[str, ...]

    def __post_init__(self):
        text(self.id)
        text(self.entity)
        ids(self.evidence_ids, empty=False)
        if not isinstance(self.pose, Pose) or self.pose.frame != self.basis.frame:
            raise ValueError("Same-frame grounded pose anchor required")


@dataclass(frozen=True)
class MotionLimits:
    max_waypoints: int = 6
    max_offset_m: float = .05
    max_rotation_rad: float = .35
    max_path_m: float = .20
    allow_gripper_changes: bool = False

    def __post_init__(self):
        integer(self.max_waypoints, low=1, high=8)
        number(self.max_offset_m, low=.00001, high=.25)
        number(self.max_rotation_rad, low=.00001, high=math.pi/2)
        number(self.max_path_m, low=.00001, high=1)
        if type(self.allow_gripper_changes) is not bool:
            raise ValueError("Explicit gripper-change permission required")


def proposal_schema(basis: Basis, anchors: tuple[PoseAnchor, ...], limits: MotionLimits) -> dict:
    ids(tuple(a.id for a in anchors), empty=False)
    for a in anchors:
        basis.require_same(a.basis)
    return {"type": "object", "additionalProperties": False,
            "required": ["basis_fingerprint", "arm", "waypoints"],
            "properties": {
                "basis_fingerprint": {"const": basis.fingerprint},
                "arm": {"enum": ["left_arm", "right_arm"]},
                "waypoints": {"type": "array", "minItems": 1, "maxItems": limits.max_waypoints,
                              "items": {"type": "object", "additionalProperties": False,
                                        "required": ["anchor_id", "offset_m", "rotvec_rad", "gripper"],
                                        "properties": {
                                            "anchor_id": {"enum": [a.id for a in anchors]},
                                            "offset_m": {"type": "array", "minItems": 3, "maxItems": 3,
                                                         "items": {"type": "number"}},
                                            "rotvec_rad": {"type": "array", "minItems": 3, "maxItems": 3,
                                                           "items": {"type": "number"}},
                                            "gripper": {"enum": ["hold", "open", "close"] if limits.allow_gripper_changes else ["hold"]}
                                        }}}}}


def _delta_pose(anchor: Pose, offset, rotvec) -> Pose:
    """Offsets and axis-angle rotations are in the named ANCHOR TCP frame."""
    import numpy as np
    a = np.asarray(anchor.matrix).reshape(4, 4)
    r = np.asarray(rotvec)
    theta = float(np.linalg.norm(r))
    delta = np.eye(4)
    if theta > 1e-12:
        k = r/theta
        skew = np.array([[0., -k[2], k[1]], [k[2], 0., -k[0]], [-k[1], k[0], 0.]])
        delta[:3, :3] = np.eye(3) + math.sin(theta)*skew + (1-math.cos(theta))*(skew@skew)
    delta[:3, 3] = offset
    return Pose(anchor.frame, tuple((a@delta).reshape(-1).tolist()))


def motion_program(reply: dict | str | bytes, *, basis: Basis, entity: str,
                   anchors: tuple[PoseAnchor, ...], start_eef: Pose, gripper: Gripper,
                   template: TemplateConfig, limits: MotionLimits, model_revision: str) -> Program:
    if isinstance(reply, dict):
        reply = strict_loads(encode(reply), max_bytes=12000)
    else:
        reply = strict_loads(reply, max_bytes=12000)
    text(model_revision)
    text(entity)
    if set(reply) != {"basis_fingerprint", "arm", "waypoints"}:
        raise ValueError("Only bounded motion proposal fields are accepted")
    if reply["basis_fingerprint"] != basis.fingerprint:
        raise PermissionError("Stale motion proposal")
    if reply["arm"] not in {"left_arm", "right_arm"}:
        raise ValueError("Explicit single arm required")
    if not isinstance(start_eef, Pose) or start_eef.frame != basis.frame:
        raise ValueError("Measured starting TCP in the current frame required")
    ids(tuple(a.id for a in anchors), empty=False)
    by_id = {a.id: a for a in anchors}
    for a in anchors:
        basis.require_same(a.basis)
        if a.entity != entity:
            raise PermissionError("Foreign object anchor")
    points = reply["waypoints"]
    if type(points) is not list or not 1 <= len(points) <= limits.max_waypoints:
        raise ValueError("Bounded keypose count required")
    steps, source = [], []
    previous = start_eef
    distance = 0.
    for p in points:
        if type(p) is not dict or set(p) != {"anchor_id", "offset_m", "rotvec_rad", "gripper"}:
            raise ValueError("Unexpected waypoint fields")
        anchor = by_id.get(p["anchor_id"])
        if anchor is None:
            raise PermissionError("Only offered anchors may be used")
        if type(p["offset_m"]) is not list or type(p["rotvec_rad"]) is not list:
            raise ValueError("Finite vectors required")
        offset = vector(tuple(p["offset_m"]), 3)
        rotvec = vector(tuple(p["rotvec_rad"]), 3)
        if sum(v*v for v in offset)**.5 > limits.max_offset_m:
            raise PermissionError("Offset outside reviewed envelope")
        if sum(v*v for v in rotvec)**.5 > limits.max_rotation_rad:
            raise PermissionError("Rotation outside reviewed envelope")
        command = p["gripper"]
        if command not in {"hold", "open", "close"} or (command != "hold" and not limits.allow_gripper_changes):
            raise PermissionError("Gripper change not authorized")
        pose = _delta_pose(anchor.pose, offset, rotvec)
        distance += sum((a-b)**2 for a, b in zip(pose.xyz, previous.xyz))**.5
        if distance > limits.max_path_m:
            raise PermissionError("Total keypose path exceeds envelope")
        steps.append(Step(Primitive.MOVE_EEF, pose, max_steps=template.step_cap,
                          max_speed_m_s=template.transit_speed_m_s))
        if command == "close":
            steps.extend((Step(Primitive.CLOSE, max_steps=template.step_cap),
                          Step(Primitive.HOLD_CHECK, max_steps=0)))
        elif command == "open":
            steps.extend((Step(Primitive.OPEN, opening_m=gripper.max_opening_m,
                               max_steps=template.step_cap),
                          Step(Primitive.RELEASE_CHECK, max_steps=0)))
        source.extend(anchor.evidence_ids)
        previous = pose
    # Include complete proposal/limits in revision: paths with the same endpoint
    # must NOT collide as catalog action IDs.
    revision = digest([model_revision, reply, limits])
    intent = Intent(Verb.STAGE, entity, "bounded_keyposes",
                    ("use_left_arm" if reply["arm"] == "left_arm" else "use_right_arm", "no_base_motion"))
    candidate = Proposal(intent, basis, Parameters(previous, instruction=revision), gripper.fingerprint,
                         "astra-keypose-proposal", revision, tuple(dict.fromkeys(source)),
                         score_kind="unscored_model_proposal")
    base = compile_program(candidate, gripper, template)
    extra = ("situated_direct_motion", "situated_whole_path", "situated_anchor_grounding")
    if any(p["gripper"] != "hold" for p in points):
        extra += ("grasp_monitor", "release_monitor", "situated_gripper_transition")
    return replace(base, steps=tuple(steps), required_checks=base.required_checks+extra,
                   recipe="bounded-astra-keyposes-v2")
