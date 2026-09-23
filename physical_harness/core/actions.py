"""Immutable derived action data. These records never replace WorldState.

Geometry, semantic labels and qualifications are trusted-adapter evidence, not
oracle truth. A model may select opaque IDs
it cannot construct executable
parameters or qualifications through the selection API.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any


def text(value: str, name: str = "text", limit: int = 512) -> str:
    if type(value) is not str or not value.strip() or len(value.encode()) > limit:
        raise ValueError(f"Invalid {name}")
    return value


def number(value: float, name: str = "number", low: float = -math.inf,
           high: float = math.inf) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"Invalid {name}")
    return float(value)


def integer(value: int, name: str = "integer", low: int = 0, high: int = 1000000) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"Invalid {name}")
    return value


def ids(value: tuple[str, ...], name: str = "ids", *, empty: bool = True,
        limit: int = 128) -> tuple[str, ...]:
    if type(value) is not tuple or len(value) > limit or (not empty and not value):
        raise ValueError(f"Expected bounded immutable {name}")
    for item in value:
        text(item, name)
    if len(set(value)) != len(value):
        raise ValueError(f"Duplicate {name}")
    return value


def vector(value: tuple[float, ...], size: int, name: str = "vector") -> tuple[float, ...]:
    if type(value) is not tuple or len(value) != size:
        raise ValueError(f"Expected immutable {size}-D {name}")
    return tuple(number(v, name) for v in value)


def unit(value: tuple[float, ...], name: str = "direction") -> tuple[float, ...]:
    value = vector(value, 3, name)
    if abs(sum(v*v for v in value) - 1) > 1e-5:
        raise ValueError(f"{name} must be a unit vector")
    return value


def plain(value: Any) -> Any:
    if is_dataclass(value):
        return plain(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        return number(value)
    if type(value) in (tuple, list):
        return [plain(v) for v in value]
    if type(value) is dict and all(type(k) is str for k in value):
        return {k: plain(v) for k, v in value.items()}
    raise ValueError("Only finite JSON data is serializable")


def encode(value: Any) -> bytes:
    return json.dumps(plain(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(encode(value)).hexdigest()


def strict_loads(value: str | bytes, *, max_bytes: int = 1000000) -> dict:
    if not isinstance(value, (str, bytes)) or len(value.encode() if isinstance(value, str) else value) > max_bytes:
        raise ValueError("Bounded JSON required")
    def unique(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError("Duplicate JSON key")
            out[k] = v
        return out
    result = json.loads(value, object_pairs_hook=unique,
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))
    if type(result) is not dict:
        raise ValueError("JSON object required")
    plain(result)
    return result


IDENTITY = (1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1.)


@dataclass(frozen=True)
class Pose:
    """T_frame_tcp, row-major, meters; never Euler angles guessed by an LLM."""
    frame: str
    matrix: tuple[float, ...] = IDENTITY

    def __post_init__(self):
        text(self.frame)
        m = vector(self.matrix, 16, "SE3")
        if any(abs(a-b) > 1e-7 for a, b in zip(m[12:], (0, 0, 0, 1))):
            raise ValueError("Invalid homogeneous transform")
        r = (m[:3], m[4:7], m[8:11])
        for i in range(3):
            for j in range(3):
                if abs(sum(r[i][k]*r[j][k] for k in range(3))-(i == j)) > 1e-5:
                    raise ValueError("Nonorthonormal rotation")
        det = (r[0][0]*(r[1][1]*r[2][2]-r[1][2]*r[2][1])
               -r[0][1]*(r[1][0]*r[2][2]-r[1][2]*r[2][0])
               +r[0][2]*(r[1][0]*r[2][1]-r[1][1]*r[2][0]))
        if abs(det-1) > 1e-5:
            raise ValueError("Rotation must be proper")
        object.__setattr__(self, "matrix", m)

    @property
    def xyz(self):
        return self.matrix[3], self.matrix[7], self.matrix[11]

    @property
    def approach(self):
        return self.matrix[2], self.matrix[6], self.matrix[10]

    def shifted(self, direction: tuple[float, ...], distance: float) -> Pose:
        direction = unit(direction)
        number(distance)
        m = list(self.matrix)
        for i, index in enumerate((3, 7, 11)):
            m[index] += direction[i]*distance
        return Pose(self.frame, tuple(m))


@dataclass(frozen=True)
class Basis:
    """An immutable reference to an existing legal capture, not another map.

    source_fingerprint comes from Hybrid Snapshot. robot/gripper/calibration
    fingerprints are operator-reviewed deployment identities. Their labels are
    not independent proof of the loaded native configuration.
    """
    episode: str
    observation_id: str
    source_fingerprint: str
    sim_time: float
    captured_wall: float
    frame: str
    frame_epoch: str
    geometry_revision: str
    execution_epoch: int
    robot_fingerprint: str
    calibration_fingerprint: str
    evidence_ids: tuple[str, ...]
    domain: str = "fixture"

    def __post_init__(self):
        for key in ("episode", "observation_id", "source_fingerprint", "frame", "frame_epoch",
                    "geometry_revision", "robot_fingerprint", "calibration_fingerprint"):
            text(getattr(self, key), key)
        number(self.sim_time, low=0)
        number(self.captured_wall, low=0)
        integer(self.execution_epoch)
        ids(self.evidence_ids, empty=False)
        if self.domain not in {"fixture", "behavior_sim"}:
            raise ValueError("Only fixture/BEHAVIOR simulation supported")

    @property
    def fingerprint(self):
        return digest(self)

    def fresh(self, now: float, max_age_s: float):
        number(now, low=0)
        number(max_age_s, low=0)
        if not 0 <= now-self.captured_wall <= max_age_s:
            raise PermissionError("Capture is stale or from the future")

    def require_same(self, other: Basis):
        if not isinstance(other, Basis) or self != other:
            raise PermissionError("Stale catalog / changed evidence or robot configuration")

    def require_continuity(self, other: Basis):
        keys = ("episode", "frame", "frame_epoch", "execution_epoch", "robot_fingerprint",
                "calibration_fingerprint", "domain")
        if not isinstance(other, Basis) or any(getattr(self, k) != getattr(other, k) for k in keys):
            raise PermissionError("Episode, execution, calibration or local frame changed")
        if other.sim_time < self.sim_time or other.captured_wall < self.captured_wall:
            raise PermissionError("Observation time regressed")


@dataclass(frozen=True)
class Gripper:
    id: str
    revision: str
    asset_digest: str
    joint_names: tuple[str, ...]
    open_positions: tuple[float, ...]
    closed_positions: tuple[float, ...]
    lower_limits: tuple[float, ...]
    upper_limits: tuple[float, ...]
    # Explicit transform T_grasp_tcp; robot-specific calibration owns it.
    grasp_to_tcp: Pose
    max_opening_m: float
    family: str = "parallel_jaw"

    def __post_init__(self):
        for s in (self.id, self.revision, self.asset_digest, self.family):
            text(s)
        ids(self.joint_names, empty=False, limit=32)
        n = len(self.joint_names)
        for value in (self.open_positions, self.closed_positions, self.lower_limits, self.upper_limits):
            vector(value, n, "gripper configuration")
        for lo, hi, a, b in zip(self.lower_limits, self.upper_limits,
                                 self.open_positions, self.closed_positions):
            if not lo <= a <= hi or not lo <= b <= hi or lo >= hi:
                raise ValueError("Invalid gripper configuration/limits")
        if not isinstance(self.grasp_to_tcp, Pose) or self.grasp_to_tcp.frame != "grasp":
            raise ValueError("T_grasp_tcp calibration required")
        number(self.max_opening_m, low=.00001, high=1)

    @property
    def fingerprint(self):
        return digest(self)


class Verb(str, Enum):
    NAVIGATE = "navigate"
    STAGE = "stage"
    GRASP = "grasp"
    PLACE = "place"
    PRESS = "press"
    PULL = "pull"
    RETRACT = "retract"
    INSPECT = "inspect"
    POLICY = "policy"


@dataclass(frozen=True)
class Intent:
    verb: Verb
    entity: str
    part: str = "whole"
    constraints: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.verb, Verb):
            raise ValueError("Typed verb required")
        text(self.entity)
        text(self.part)
        ids(self.constraints)


@dataclass(frozen=True)
class Parameters:
    """Filled by geometry/code, never by the model's select-action tool."""
    pose: Pose | None = None
    direction: tuple[float, ...] | None = None
    standoff_m: float = .05
    travel_m: float = 0.
    opening_m: float | None = None
    attachment_id: str | None = None
    instruction: str | None = None

    def __post_init__(self):
        if self.pose is not None and not isinstance(self.pose, Pose):
            raise ValueError("Typed pose required")
        if self.direction is not None:
            unit(self.direction)
        number(self.standoff_m, low=0, high=.5)
        number(self.travel_m, low=0, high=1)
        if self.opening_m is not None:
            number(self.opening_m, low=0, high=1)
        if self.attachment_id is not None:
            text(self.attachment_id)
        if self.instruction is not None:
            text(self.instruction, limit=4096)


@dataclass(frozen=True)
class Proposal:
    intent: Intent
    basis: Basis
    parameters: Parameters
    gripper_fingerprint: str
    generator: str
    generator_revision: str
    evidence_ids: tuple[str, ...]
    score: float = 0.
    score_kind: str = "uncalibrated_rank"

    def __post_init__(self):
        if not isinstance(self.intent, Intent) or not isinstance(self.basis, Basis):
            raise ValueError("Typed intent and evidence basis required")
        if not isinstance(self.parameters, Parameters):
            raise ValueError("Typed parameters required")
        for s in (self.gripper_fingerprint, self.generator, self.generator_revision, self.score_kind):
            text(s)
        ids(self.evidence_ids, empty=False)
        number(self.score)  # Never assume a model logit is a success probability.
        if self.parameters.pose and self.parameters.pose.frame != self.basis.frame:
            raise ValueError("Candidate pose is in the wrong frame")
        if self.intent.verb not in {Verb.INSPECT, Verb.POLICY} and self.parameters.pose is None:
            raise ValueError("Metric candidate requires a pose")
        if self.intent.verb in {Verb.PRESS, Verb.PULL} and self.parameters.direction is None:
            raise ValueError("Contact candidate requires an observed direction")
        if self.intent.verb == Verb.PLACE and not self.parameters.attachment_id:
            raise ValueError("Place requires a measured attachment identity")
        if self.intent.verb == Verb.POLICY and not self.parameters.instruction:
            raise ValueError("Frozen policy instruction required")

    @property
    def id(self):
        return "action:"+digest(self)[:32]


class Primitive(str, Enum):
    MOVE_BASE = "move_base"
    MOVE_EEF = "move_eef"
    CLOSE = "close_gripper"
    OPEN = "open_gripper"
    HOLD_CHECK = "measured_grasp"
    RELEASE_CHECK = "measured_release"
    PRESS = "guarded_press"
    PULL = "guarded_linear_pull"
    INSPECT = "passive_inspect"
    POLICY = "frozen_policy"


@dataclass(frozen=True)
class Step:
    kind: Primitive
    pose: Pose | None = None
    end_pose: Pose | None = None
    opening_m: float | None = None
    max_steps: int = 60
    max_speed_m_s: float = .03
    max_policy_calls: int = 0
    max_policy_chunks: int = 0

    def __post_init__(self):
        if not isinstance(self.kind, Primitive):
            raise ValueError("Typed primitive required")
        integer(self.max_steps, low=0, high=100000)
        integer(self.max_policy_calls)
        integer(self.max_policy_chunks)
        if self.kind != Primitive.POLICY and (self.max_policy_calls or self.max_policy_chunks):
            raise ValueError("Only policy steps allocate inference budget")
        number(self.max_speed_m_s, low=.00001, high=1)
        for p in (self.pose, self.end_pose):
            if p is not None and not isinstance(p, Pose):
                raise ValueError("Typed step pose required")
        if self.opening_m is not None:
            number(self.opening_m, low=0, high=1)


@dataclass(frozen=True)
class Program:
    proposal: Proposal
    steps: tuple[Step, ...]
    required_checks: tuple[str, ...]
    robot_dofs: int
    recipe: str

    def __post_init__(self):
        if not isinstance(self.proposal, Proposal):
            raise ValueError("Typed proposal required")
        if type(self.steps) is not tuple or not 1 <= len(self.steps) <= 32:
            raise ValueError("Bounded immutable program required")
        if not all(isinstance(s, Step) for s in self.steps):
            raise ValueError("Typed steps required")
        ids(self.required_checks, empty=False)
        integer(self.robot_dofs, low=1, high=256)
        text(self.recipe)

    @property
    def fingerprint(self):
        return digest(self)

    @property
    def max_steps(self):
        return sum(s.max_steps for s in self.steps)


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool | None
    evidence_ids: tuple[str, ...]
    note: str = ""

    def __post_init__(self):
        text(self.name)
        if self.passed is not None and type(self.passed) is not bool:
            raise ValueError("Check must be true, false or unknown")
        ids(self.evidence_ids, empty=False)
        if type(self.note) is not str or len(self.note.encode()) > 1024:
            raise ValueError("Bounded diagnostic note required")


@dataclass(frozen=True)
class Review:
    """Exact program AND current-capture binding, including all contact phases."""
    program_fingerprint: str
    basis_fingerprint: str
    qualification_id: str
    domain: str
    checks: tuple[Check, ...]

    def __post_init__(self):
        for s in (self.program_fingerprint, self.basis_fingerprint, self.qualification_id):
            text(s)
        if self.domain not in {"fixture", "behavior_sim"}:
            raise ValueError("Invalid review domain")
        if type(self.checks) is not tuple or not all(isinstance(c, Check) for c in self.checks):
            raise ValueError("Typed review checks required")
        ids(tuple(c.name for c in self.checks), empty=False)

    def failures(self, program: Program, basis: Basis) -> tuple[str, ...]:
        if (self.program_fingerprint, self.basis_fingerprint, self.domain) != (
            program.fingerprint, basis.fingerprint, basis.domain
        ):
            return ("review_binding_mismatch",)
        values = {c.name: c.passed for c in self.checks}
        bad = [k for k in program.required_checks if values.get(k) is not True]
        bad.extend(c.name for c in self.checks if c.passed is not True and c.name not in bad)
        return tuple(bad)
