"""Object-centric candidate generation. Semantic grounding remains an input.

Grasp ranking is not a grasp proof. A planar patch is not automatically a button
callers must select an explicitly grounded semantic part and retain its evidence.
"""
from __future__ import annotations

import math

import numpy as np

from physical_harness.core.actions import (
    Basis,
    Gripper,
    Intent,
    Parameters,
    Pose,
    Proposal,
    Verb,
    ids,
    integer,
    number,
    unit,
)
from physical_harness.perception.geometry import (
    ObjectCloud,
    Surface,
    compose_tcp,
    pose_from_approach,
)


def analytic_parallel_grasps(cloud: ObjectCloud, gripper: Gripper, *,
                             opening_margin_m: float = .005, max_candidates: int = 8):
    """PCA/OBB hypotheses for a simple gripper, NEVER force-closure certification.

    Partial point clouds underestimate hidden object extent. These proposals must
    pass a separate full-object/scene collision and semantic-contact review.
    """
    if gripper.family != "parallel_jaw":
        raise ValueError("Analytic generator is parallel-jaw only")
    integer(max_candidates, low=1, high=32)
    number(opening_margin_m, low=0, high=.1)
    points = np.asarray(cloud.points)
    center = points.mean(axis=0)
    _, _, axes = np.linalg.svd(points-center, full_matrices=False)
    projected = (points-center) @ axes.T
    widths = np.ptp(projected, axis=0)
    result = []
    for closing in range(3):
        width = float(widths[closing]+2*opening_margin_m)
        if width <= 1e-5 or width > gripper.max_opening_m:
            continue
        for approach in range(3):
            if approach == closing:
                continue
            for sign in (1, -1):
                x, z = axes[closing], sign*axes[approach]
                y = np.cross(z, x)
                matrix = np.eye(4)
                matrix[:3, :3] = np.column_stack((x, y, z))
                matrix[:3, 3] = center
                grasp = Pose(cloud.basis.frame, tuple(float(v) for v in matrix.ravel()))
                tcp = compose_tcp(grasp, gripper.grasp_to_tcp)
                result.append(Proposal(Intent(Verb.GRASP, cloud.entity, cloud.part), cloud.basis,
                                       Parameters(tcp, opening_m=width), gripper.fingerprint,
                                       "analytic-pca", "1", cloud.evidence_ids,
                                       score=-width, score_kind="width_heuristic_not_probability"))
    return tuple(result[:max_candidates])


def press_candidate(surface: Surface, gripper: Gripper, *, travel_m: float,
                    standoff_m: float = .05) -> Proposal:
    direction = tuple(-v for v in surface.outward_normal)
    pose = pose_from_approach(surface.cloud.basis.frame, surface.point, direction)
    # This is a contact TCP pose, not a grasp pose; no grasp-frame transform here.
    return Proposal(Intent(Verb.PRESS, surface.cloud.entity, surface.cloud.part), surface.cloud.basis,
                    Parameters(pose, direction, standoff_m, travel_m), gripper.fingerprint,
                    "observed-planar-contact", "1", surface.cloud.evidence_ids,
                    -surface.residual_p95_m, "negative_plane_residual_not_probability")


def pull_candidate(*, basis: Basis, entity: str, part: str, gripper: Gripper,
                   grasp_tcp: Pose, prismatic_direction: tuple, travel_m: float,
                   evidence_ids: tuple[str, ...]) -> Proposal:
    unit(prismatic_direction)
    return Proposal(Intent(Verb.PULL, entity, part), basis,
                    Parameters(grasp_tcp, prismatic_direction, travel_m=travel_m,
                               opening_m=gripper.max_opening_m), gripper.fingerprint,
                    "observed-linear-articulation", "1", evidence_ids)


def pose_candidate(*, basis: Basis, intent: Intent, pose: Pose, gripper: Gripper,
                   evidence_ids: tuple[str, ...], attachment_id: str | None = None) -> Proposal:
    if intent.verb not in {Verb.NAVIGATE, Verb.STAGE, Verb.PLACE, Verb.RETRACT}:
        raise ValueError("Use a verb-specific contact/grasp generator")
    return Proposal(intent, basis, Parameters(pose, attachment_id=attachment_id,
                                             opening_m=gripper.max_opening_m
                                             if intent.verb == Verb.PLACE else None),
                    gripper.fingerprint, "observed-pose-candidate", "1", evidence_ids)


def inspect_candidate(basis: Basis, gripper: Gripper, entity: str = "scene") -> Proposal:
    return Proposal(Intent(Verb.INSPECT, entity), basis, Parameters(), gripper.fingerprint,
                    "passive-reobservation", "1", basis.evidence_ids)


def policy_candidate(basis: Basis, gripper: Gripper, *, entity: str, instruction: str,
                     policy_fingerprint: str) -> Proposal:
    """Only an explicit candidate, not automatic fallback after geometric failure."""
    return Proposal(Intent(Verb.POLICY, entity), basis, Parameters(instruction=instruction),
                    gripper.fingerprint, "frozen-policy", policy_fingerprint, basis.evidence_ids)


def filter_grasp_region(grasps: tuple[Proposal, ...], *, allowed_region: ObjectCloud,
                        closing_contacts: callable) -> tuple[Proposal, ...]:
    """Require actual closing-contact support on selected part, not wrist proximity.

    closing_contacts(candidate, region) is a qualified contact-volume test. Using
    only distance from the grasp origin to the handle can reject good grasps and
    accept bad ones, so this module deliberately does not substitute that shortcut.
    """
    out = []
    for p in grasps:
        p.basis.require_same(allowed_region.basis)
        if (p.intent.entity, p.intent.part) != (allowed_region.entity, allowed_region.part):
            raise ValueError("Semantic region mismatch")
        if closing_contacts(p, allowed_region) is True:
            out.append(p)
    return tuple(out)


def grasp_distance(a: Pose, b: Pose) -> tuple[float, float]:
    if a.frame != b.frame:
        raise ValueError("Frame mismatch")
    ra, rb = (np.asarray(p.matrix).reshape(4, 4)[:3, :3] for p in (a, b))
    angle = math.acos(float(np.clip((np.trace(ra.T@rb)-1)/2, -1, 1)))
    distance = math.dist(a.xyz, b.xyz)
    return distance, angle


def diverse_grasps(proposals: tuple[Proposal, ...], *, max_count: int = 8,
                   translation_m: float = .02, angle_rad: float = .2) -> tuple[Proposal, ...]:
    integer(max_count, low=1, high=32)
    number(translation_m, low=0)
    number(angle_rad, low=0, high=math.pi)
    ids(tuple(p.id for p in proposals))
    # Only rank comparable generator scores; never compare two unrelated models' logits.
    if len({(p.generator, p.generator_revision, p.score_kind) for p in proposals}) > 1:
        raise ValueError("Diversity ranking requires comparable score provenance")
    chosen = []
    for p in sorted(proposals, key=lambda x: (-x.score, x.id)):
        if p.intent.verb != Verb.GRASP:
            raise ValueError("Grasp candidates required")
        if all((lambda d: d[0] >= translation_m or d[1] >= angle_rad)(
                grasp_distance(p.parameters.pose, q.parameters.pose)) for q in chosen):
            chosen.append(p)
        if len(chosen) == max_count:
            break
    return tuple(chosen)
