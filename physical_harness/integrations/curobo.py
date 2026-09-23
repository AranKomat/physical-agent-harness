"""Classical free-space planner contract and an audited cuRoboV2 adapter.

Planning outputs are proposals, not actuator authority. No robot configuration,
collision world, support surface or force feedback is invented here. This module
never imports CUDA/Torch/cuRobo until the explicit backend is actually invoked.
"""
from __future__ import annotations

import math
import threading
from dataclasses import dataclass

from physical_harness.core.actions import Basis, Pose, digest, ids, integer, number, text, vector

CUROBO_REVISION = "78fd485fa82d9b9a063fb4985e371814587e666a"


@dataclass(frozen=True)
class JointLimits:
    names: tuple[str, ...]
    lower: tuple[float, ...]
    upper: tuple[float, ...]
    velocity: tuple[float, ...]
    acceleration: tuple[float, ...]

    def __post_init__(self):
        ids(self.names, empty=False, limit=128)
        n = len(self.names)
        for v in (self.lower, self.upper, self.velocity, self.acceleration):
            vector(v, n)
        for lo, hi, v, a in zip(self.lower, self.upper, self.velocity, self.acceleration):
            if lo >= hi or v <= 0 or a <= 0:
                raise ValueError("Joint limits/speed/acceleration must be physically configured")


@dataclass(frozen=True)
class PlanRequest:
    id: str
    basis: Basis
    start: tuple[float, ...]
    target: Pose
    tool_frame: str
    limits: JointLimits
    fixed_joint_names: tuple[str, ...]
    fixed_joint_positions: tuple[float, ...]
    scene_digest: str
    scene_evidence: tuple[str, ...]
    dt: float
    max_samples: int
    robot_config_digest: str

    def __post_init__(self):
        text(self.id)
        text(self.tool_frame)
        text(self.scene_digest)
        text(self.robot_config_digest)
        if not isinstance(self.basis, Basis) or not isinstance(self.target, Pose) or self.target.frame != self.basis.frame:
            raise ValueError("Current named-frame planning target required")
        if not isinstance(self.limits, JointLimits):
            raise ValueError("Explicit named joint limits required")
        vector(self.start, len(self.limits.names))
        if any(not lo <= x <= hi for x, lo, hi in zip(self.start, self.limits.lower, self.limits.upper)):
            raise ValueError("Start state violates joint bounds")
        ids(self.fixed_joint_names)
        vector(self.fixed_joint_positions, len(self.fixed_joint_names))
        if set(self.fixed_joint_names) & set(self.limits.names):
            raise ValueError("Joint cannot be fixed and controlled simultaneously")
        ids(self.scene_evidence, empty=False)
        number(self.dt, low=.00001, high=1)
        integer(self.max_samples, low=2, high=100000)

    @property
    def fingerprint(self):
        return digest(self)


@dataclass(frozen=True)
class JointTrajectory:
    request_fingerprint: str
    basis: Basis
    joint_names: tuple[str, ...]
    positions: tuple[tuple[float, ...], ...]
    dt: float
    scene_digest: str
    backend: str
    backend_revision: str
    scene_receipt: str

    def validate(self, request: PlanRequest, *, start_tolerance=1e-5):
        if self.request_fingerprint != request.fingerprint or self.basis != request.basis or self.scene_digest != request.scene_digest:
            raise PermissionError("Stale planner result or changed collision world")
        if self.joint_names != request.limits.names or self.dt != request.dt:
            raise PermissionError("Planner joint order or control time base changed")
        text(self.backend)
        text(self.backend_revision)
        text(self.scene_receipt)
        if type(self.positions) is not tuple or not 2 <= len(self.positions) <= request.max_samples:
            raise ValueError("Empty or over-budget trajectory")
        for q in self.positions:
            vector(q, len(self.joint_names))
            if any(not lo <= x <= hi for x, lo, hi in zip(q, request.limits.lower, request.limits.upper)):
                raise ValueError("Trajectory joint limits violated")
        number(start_tolerance, low=0)
        if max(abs(a-b) for a, b in zip(self.positions[0], request.start)) > start_tolerance:
            raise PermissionError("Trajectory starts somewhere other than measured joints")
        previous_v = [0.] * len(self.joint_names)
        for a, b in zip(self.positions, self.positions[1:]):
            v = [(y-x)/self.dt for x, y in zip(a, b)]
            if any(abs(x) > limit+1e-7 for x, limit in zip(v, request.limits.velocity)):
                raise ValueError("Trajectory exceeds configured velocity")
            if any(abs(x-p)/self.dt > limit+1e-7 for x, p, limit in zip(v, previous_v, request.limits.acceleration)):
                raise ValueError("Trajectory exceeds configured acceleration")
            previous_v = v
        if any(abs(v)/self.dt > limit+1e-7 for v, limit in zip(previous_v, request.limits.acceleration)):
            raise ValueError("Trajectory cannot end at rest within acceleration bound")
        return self


@dataclass(frozen=True)
class SceneReceipt:
    request_fingerprint: str
    scene_digest: str
    robot_config_digest: str
    fixed_joint_names: tuple[str, ...]
    fixed_joint_positions: tuple[float, ...]
    tool_frame: str
    planner_frame: str
    fully_updated: bool
    evidence_ids: tuple[str, ...]

    def require(self, request: PlanRequest):
        if (self.request_fingerprint, self.scene_digest, self.robot_config_digest, self.fixed_joint_names,
            self.fixed_joint_positions, self.tool_frame, self.planner_frame) != (
            request.fingerprint, request.scene_digest, request.robot_config_digest, request.fixed_joint_names,
            request.fixed_joint_positions, request.tool_frame, request.basis.frame
        ):
            raise PermissionError("Planner scene/kinematic mounting contract mismatch")
        ids(self.evidence_ids, empty=False)
        if self.fully_updated is not True:
            raise PermissionError("Unconfirmed planner world update")


def quaternion_wxyz(pose: Pose):
    """Stable SE(3) rotation conversion; no guessed Euler convention."""
    import numpy as np
    r = np.array(pose.matrix).reshape(4,4)[:3,:3]
    t = float(np.trace(r))
    if t > 0:
        s = math.sqrt(t+1)*2
        q = (s/4, (r[2,1]-r[1,2])/s, (r[0,2]-r[2,0])/s, (r[1,0]-r[0,1])/s)
    else:
        i = int(np.argmax(np.diag(r)))
        j, k = (i+1)%3, (i+2)%3
        s = math.sqrt(1+r[i,i]-r[j,j]-r[k,k])*2
        xyz = [0.,0.,0.]
        xyz[i] = s/4
        xyz[j] = (r[j,i]+r[i,j])/s
        xyz[k] = (r[k,i]+r[i,k])/s
        q = ((r[k,j]-r[j,k])/s, *xyz)
    n = math.sqrt(sum(float(x*x) for x in q))
    return tuple(float(x/n) for x in q)


class CuroboV2Planner:
    """Thin adapter to the inspected MotionPlanner.plan_pose API, not legacy MotionGen.

    Operator supplies the loaded, pinned planner and a scene-install callback. The
    callback MUST replace the collision scene and fixed-joint state from legal
    sensors/current robot state, with full-robot/payload geometry as applicable.
    A mock SceneReceipt does not qualify these facts. The adapter never calls
    plan_grasp (whose upstream demo disables finger collisions).
    """
    def __init__(self, *, planner, install_scene, source_revision: str,
                 enabled: bool = False, api=None, clock=None, source_checkout=None):
        import time
        if source_revision != CUROBO_REVISION:
            raise PermissionError("cuRobo API revision must be explicitly re-audited")
        if type(enabled) is not bool:
            raise ValueError("Explicit planning opt-in required")
        self.planner, self.install_scene, self.enabled = planner, install_scene, enabled
        self.api, self.clock = api, clock or time.monotonic
        self.source_checkout = source_checkout
        self._source_verified = False
        self.lock = threading.Lock()

    def plan(self, request: PlanRequest, *, deadline: float) -> JointTrajectory:
        if not self.enabled:
            raise PermissionError("cuRobo inference disabled")
        if not self.lock.acquire(blocking=False):
            raise RuntimeError("Planner world is already in use")
        try:
            request.basis.fresh(self.clock(), 2.)
            if self.clock() >= deadline:
                raise TimeoutError("Planning deadline")
            planner = self.planner
            if tuple(planner.joint_names) != request.limits.names or tuple(planner.tool_frames) != (request.tool_frame,):
                raise PermissionError("Only exact configured joint order and one explicit tool are supported")
            dt = float(planner.trajopt_solver.config.interpolation_dt)
            if abs(dt-request.dt) > 1e-12:
                raise PermissionError("Do not silently resample the native control rate")
            receipt = self.install_scene(planner, request, deadline)
            if not isinstance(receipt, SceneReceipt):
                raise ValueError("Typed scene-install receipt required")
            receipt.require(request)
            if self.api is None:
                if not self._source_verified:
                    verify_curobo_checkout(self.source_checkout, planner)
                    self._source_verified = True
                import torch
                from curobo.types import GoalToolPose, JointState
                api = (torch, GoalToolPose, JointState)
            else:
                api = self.api  # Test injection only; real path uses audited upstream classes.
            torch, GoalToolPose, JointState = api
            device = planner.default_joint_state.position.device
            dtype = planner.default_joint_state.position.dtype
            start = JointState.from_position(torch.tensor([request.start], device=device, dtype=dtype),
                                             joint_names=list(request.limits.names))
            goal = GoalToolPose(tool_frames=list(planner.tool_frames),
                                position=torch.tensor([[[[request.target.xyz]]]], device=device, dtype=dtype),
                                quaternion=torch.tensor([[[[quaternion_wxyz(request.target)]]]], device=device, dtype=dtype))
            if self.clock() >= deadline:
                raise TimeoutError("Planning deadline before solve")
            result = planner.plan_pose(goal, start)
            if self.clock() > deadline:
                raise TimeoutError("Late planner output; no motion authorized")
            if result is None or int(result.success.numel()) != 1 or not bool(result.success.reshape(-1)[0].item()):
                raise ValueError("Planner did not return one successful solution")
            q = result.get_interpolated_plan().position.detach().cpu().numpy()
            if q.ndim == 3 and q.shape[0] == 1:
                q = q[0]
            if q.ndim != 2 or q.shape[1] != len(request.limits.names):
                raise ValueError("Unexpected planner trajectory dimensions")
            trajectory = JointTrajectory(request.fingerprint, request.basis, request.limits.names,
                                         tuple(tuple(float(x) for x in row) for row in q), request.dt,
                                         request.scene_digest, "curobo-v2-plan-pose", CUROBO_REVISION, digest(receipt))
            return trajectory.validate(request)
        finally:
            self.lock.release()


def verify_curobo_checkout(path, planner):
    """Verify the operator-provisioned immutable upstream code; never install it.

    Robot assets and the actual collision/fixed-joint state still need the
    separate SceneReceipt and native reviewers. Run in a read-only deployment:
    this check does not defend against concurrent modification of trusted code.
    """
    import importlib
    import subprocess
    from pathlib import Path
    if path is None:
        raise PermissionError("Explicit pinned cuRobo source checkout required")
    root = Path(path).resolve(strict=True)
    def git(*args):
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                              text=True, check=True, timeout=5).stdout.strip()
    if git("rev-parse", "HEAD") != CUROBO_REVISION:
        raise PermissionError("cuRobo checkout revision changed")
    if git("status", "--porcelain", "--untracked-files=no"):
        raise PermissionError("cuRobo tracked source is modified")
    module_name = type(planner).__module__
    if not module_name.startswith("curobo."):
        raise PermissionError("Loaded planner is not from the reviewed cuRobo package")
    module = importlib.import_module(module_name)
    loaded = Path(module.__file__).resolve(strict=True)
    if root not in loaded.parents:
        raise PermissionError("Loaded cuRobo module belongs to another installation")
    return CUROBO_REVISION
