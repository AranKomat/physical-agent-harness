"""Next-best-view ranking from observed geometry and explicit uncertainty.

Scores are explainable proxies, not measured information gain. Unseen shape,
semantic front/back, true occlusion from a novel view, and safe reachability are
not inferred from one cloud. Native view/motion checks are still mandatory.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

from physical_harness.core.actions import Basis, integer, plain
from physical_harness.perception.geometry import Intrinsics, ObjectCloud
from physical_harness.planning.inspection import InspectionCandidate
from physical_harness.world.inventory import CanonicalView


@dataclass(frozen=True)
class ViewAssessment:
    candidate_id: str
    in_frame_fraction: float
    supported_visible_fraction: float
    unknown_visibility_fraction: float
    projected_area_fraction: float
    novel_direction: float
    travel_m: float
    score: float
    eligible_hint: bool
    reasons: tuple[str, ...]


def assess_views(candidates: tuple[InspectionCandidate, ...], *, current: Basis,
                 cloud: ObjectCloud, intrinsics: Intrinsics,
                 prior_views: tuple[CanonicalView, ...] = (), visibility=None,
                 feasible=None, maximum: int = 4) -> tuple[tuple[InspectionCandidate, ViewAssessment], ...]:
    """Compute point projection, novelty and travel penalty, then rank.

    visibility(camera_xyz, observed_point, current) -> True/False/None, from a
    qualified local geometry query. feasible(candidate, current) -> bool/None.
    Missing callbacks are unknown, not an all-clear certificate. Without them
    callers still get diagnostics but candidates are not eligible hints.
    """
    import numpy as np
    integer(maximum, low=1, high=16)
    current.require_same(cloud.basis)
    if type(candidates) is not tuple or len(candidates) > 32:
        raise ValueError("Bounded viewpoint candidates required")
    points = np.array(cloud.points, dtype=float)
    # Bounded deterministic diagnostic sample; not the collision surface itself.
    if len(points) > 512:
        points = points[np.linspace(0, len(points)-1, 512, dtype=int)]
    result = []
    for candidate in candidates:
        current.require_same(candidate.basis)
        T = np.array(candidate.camera_pose.matrix).reshape(4,4)
        local = (points-T[:3,3]) @ T[:3,:3]
        good = local[:,2] > 1e-6
        uv = np.zeros((len(local),2))
        uv[good,0] = intrinsics.fx*local[good,0]/local[good,2]+intrinsics.cx
        uv[good,1] = intrinsics.fy*local[good,1]/local[good,2]+intrinsics.cy
        good &= (uv[:,0] >= 0) & (uv[:,0] < intrinsics.width) & (uv[:,1] >= 0) & (uv[:,1] < intrinsics.height)
        fraction = float(np.mean(good))
        verdicts = [visibility(candidate.camera_pose.xyz, tuple(p), current) if visibility else None for p in points[good]]
        if any(v is not None and type(v) is not bool for v in verdicts):
            raise ValueError("Visibility query must be three-valued")
        visible = sum(v is True for v in verdicts)/len(points)
        unknown = sum(v is None for v in verdicts)/len(points)
        uv_good = uv[good]
        area = 0. if len(uv_good) < 2 else float(np.prod(np.ptp(uv_good, axis=0))/(intrinsics.width*intrinsics.height))
        direction = np.array(candidate.camera_pose.xyz)-np.array(cloud.centroid)
        norm = np.linalg.norm(direction)
        novelty = 1.
        comparable = [v for v in prior_views if v.direction is not None and v.direction_frame == current.frame and
                      v.frame.basis.frame_epoch == current.frame_epoch]
        if norm > 1e-8 and comparable:
            novelty = min(math.acos(float(np.clip(np.dot(direction/norm, v.direction), -1, 1)))/math.pi for v in comparable)
        feasibility = feasible(candidate, current) if feasible else None
        if feasibility is not None and type(feasibility) is not bool:
            raise ValueError("Feasibility query must be three-valued")
        score = .35*fraction + .25*visible + .2*math.sqrt(max(0,area)) + .2*novelty - .3*unknown - .1*candidate.travel_m
        eligible = feasibility is True and fraction > 0 and unknown == 0 and visible > 0
        reasons = []
        if feasibility is not True:
            reasons.append("view_motion_unqualified")
        if unknown:
            reasons.append("visibility_unknown")
        if not visible:
            reasons.append("no_supported_visible_surface")
        assessment = ViewAssessment(candidate.id, fraction, visible, unknown, area, novelty,
                                    candidate.travel_m, score, eligible, tuple(reasons))
        # Existing expected_gain stays an uncalibrated bounded ranking hint.
        scored = replace(candidate, expected_gain=max(0., min(1., score)), assessor="observed-view-proxy-v3")
        result.append((scored, assessment))
    return tuple(sorted(result, key=lambda v: (not v[1].eligible_hint, -v[1].score, v[1].candidate_id))[:maximum])


def assessment_report(results) -> dict:
    return {"assessments": [plain(a) for _, a in results],
            "information_gain_is_heuristic": True, "motion_authority": False}
