"""Active perception is an information goal, not a pose invented by the executive."""
from __future__ import annotations

import math
from dataclasses import dataclass

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
    ids,
    number,
    plain,
    unit,
    vector,
)
from .visual import GoalKind, VisualGoal


@dataclass(frozen=True)
class InspectionCandidate:
    goal: VisualGoal
    basis: Basis
    camera_pose: Pose
    robot_pose: Pose
    motion_verb: Verb
    expected_gain: float
    travel_m: float
    evidence_ids: tuple[str, ...]
    assessor: str

    def __post_init__(self):
        from ..action_compiler.types import text
        if not isinstance(self.goal, VisualGoal) or self.goal.kind != GoalKind.INFORMATION:
            raise ValueError("Inspection needs an information goal")
        if not isinstance(self.basis, Basis):
            raise ValueError("Basis required")
        for pose in (self.camera_pose, self.robot_pose):
            if not isinstance(pose, Pose) or pose.frame != self.basis.frame:
                raise ValueError("Inspection pose frame mismatch")
        if self.motion_verb not in {Verb.STAGE, Verb.NAVIGATE}:
            raise ValueError("View change uses an explicitly qualified arm/base primitive")
        number(self.expected_gain, low=0, high=1)
        number(self.travel_m, low=0, high=5)
        ids(self.evidence_ids, empty=False)
        text(self.assessor)

    @property
    def id(self):
        return "view:" + digest(self)[:24]


def orbit_views(*, basis: Basis, current_camera: Pose, target_xyz: tuple[float, ...],
                up: tuple[float, ...], up_evidence: str, angles_rad: tuple[float, ...],
                max_camera_travel_m: float) -> tuple[Pose, ...]:
    """Geometric CAMERA proposals only. No IK, visibility or clearance is invented.

    Up is supplied from reviewed calibration, not assumed local-map +Z. A face
    called 'front' cannot be inferred just by circling an unknown side view.
    """
    import numpy as np

    from ..action_compiler.types import text
    text(up_evidence)
    unit(up)
    vector(target_xyz, 3)
    number(max_camera_travel_m, low=.001, high=2)
    if current_camera.frame != basis.frame or type(angles_rad) is not tuple or len(angles_rad) > 16:
        raise ValueError("Bounded same-frame orbit required")
    u = np.asarray(up)
    delta = np.asarray(current_camera.xyz) - target_xyz
    if np.linalg.norm(delta) < .001:
        raise ValueError("Camera coincides with target")
    views = []
    for angle in angles_rad:
        number(angle, low=-math.pi/2, high=math.pi/2)
        rotated = delta*math.cos(angle) + np.cross(u, delta)*math.sin(angle) + u*np.dot(u, delta)*(1-math.cos(angle))
        point = np.asarray(target_xyz) + rotated
        if np.linalg.norm(point-current_camera.xyz) > max_camera_travel_m:
            continue
        z = np.asarray(target_xyz) - point
        z /= np.linalg.norm(z)
        x = np.cross(z, u)
        if np.linalg.norm(x) < 1e-6:
            continue
        x /= np.linalg.norm(x)
        y = np.cross(z, x)  # optical y down; z forward; right handed
        m = np.eye(4)
        m[:3, :3] = np.column_stack((x, y, z))
        m[:3, 3] = point
        views.append(Pose(basis.frame, tuple(m.reshape(-1).tolist())))
    return tuple(views)


def rank_inspections(candidates: tuple[InspectionCandidate, ...], current: Basis,
                     *, maximum=4) -> tuple[InspectionCandidate, ...]:
    from ..action_compiler.types import integer
    integer(maximum, low=1, high=16)
    if type(candidates) is not tuple or len(candidates) > 128:
        raise ValueError("Bounded candidates required")
    for c in candidates:
        current.require_same(c.basis)
    # These scores are hypotheses, NOT calibrated information gain or motion approval.
    return tuple(sorted((c for c in candidates if c.expected_gain > 0),
                        key=lambda c: (-c.expected_gain, c.travel_m, c.id))[:maximum])


def inspection_program(candidate: InspectionCandidate, gripper: Gripper,
                       template: TemplateConfig) -> Program:
    """Qualified view change followed by passive capture. Completion stays external."""
    from dataclasses import replace
    intent = Intent(candidate.motion_verb, candidate.goal.entity, "inspection_view")
    proposal = Proposal(intent, candidate.basis,
                        Parameters(candidate.robot_pose, instruction=digest(plain(candidate))),
                        gripper.fingerprint, "active-view-geometry", "1", candidate.evidence_ids,
                        candidate.expected_gain, "heuristic_view_gain_not_safety")
    base = compile_program(proposal, gripper, template)
    extra = ("situated_view_kinematics", "situated_information_target", "situated_camera_calibration")
    return replace(base, steps=base.steps + (Step(Primitive.INSPECT, max_steps=0),),
                   required_checks=base.required_checks + extra, recipe="active-inspection-v2")
