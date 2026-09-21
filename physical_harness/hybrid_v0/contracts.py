"""Hybrid V0 contracts. Qualifications are operator attestations, not safety proofs.

Sensor packets reuse LegalObservation. No simulator object, score, global pose,
raw-torque channel, neural weights, or provider SDK is accepted here.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from enum import Enum

from ..adapters.behavior import LegalObservation


def encoded(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def text(value, name="text", maximum=512):
    if not isinstance(value, str) or not value.strip() or len(value.encode()) > maximum:
        raise ValueError(f"Invalid {name}")
    return value


def real(value, name="number", low=0.0, high=math.inf):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"Invalid {name}")
    return float(value)


def integer(value, name="integer", minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"Invalid {name}")
    return value


def identifiers(value, name="IDs", maximum=256):
    if not isinstance(value, tuple) or len(value) > maximum:
        raise ValueError(f"Immutable bounded {name} required")
    for item in value:
        text(item, name)
    if len(set(value)) != len(value):
        raise ValueError(f"Duplicate {name}")
    return value


class Regime(str, Enum):
    NAVIGATE = "navigate"
    STAGE = "stage"
    POLICY = "policy"
    RETREAT = "retreat"


# Whole-robot ownership for the complete composite, including handoffs. Aliases
# cover the public harness's arm/base locks and both trunk/torso spellings.
ROBOT_RESOURCES = frozenset({"robot", "base", "torso", "trunk", "left_arm", "right_arm",
                             "left_gripper", "right_gripper", "head"})


@dataclass(frozen=True)
class PolicyIdentity:
    """Pin the WHOLE inference recipe, not merely a model name or action width."""
    checkpoint: str
    revision: str
    weights_digest: str
    observation_codec: str
    action_codec: str
    normalization: str
    inference_recipe: str
    instruction_contract: str
    action_dimensions: int = 23

    def __post_init__(self):
        for k, v in asdict(self).items():
            if k != "action_dimensions":
                text(v, k)
        integer(self.action_dimensions, minimum=1)

    @property
    def fingerprint(self):
        return digest(asdict(self))


@dataclass(frozen=True)
class Snapshot:
    """An immutable, already legal capture in one host monotonic clock domain.

    captured_wall is exposure/capture time, NOT the time an old frame was read
    from disk. frame_epoch changes on localization reset/relocalization. Geometry
    revision is an opaque identifier owned by the qualified sensor-map adapter.
    """
    envelope_json: str
    captured_wall: float
    frame_epoch: str
    geometry_revision: str

    def __post_init__(self):
        real(self.captured_wall, "captured_wall")
        text(self.frame_epoch, "frame_epoch")
        text(self.geometry_revision, "geometry_revision")
        if not isinstance(self.envelope_json, str) or len(self.envelope_json.encode()) > 256_000:
            raise ValueError("Bounded legal envelope required")
        value = LegalObservation.from_envelope(json.loads(self.envelope_json)).to_envelope()
        object.__setattr__(self, "envelope_json", encoded(value).decode())

    @classmethod
    def from_envelope(cls, envelope, *, captured_wall, frame_epoch, geometry_revision):
        # Validate BEFORE JSON serialization can coerce non-JSON keys or numbers.
        value = LegalObservation.from_envelope(envelope).to_envelope()
        return cls(encoded(value).decode(), captured_wall, frame_epoch, geometry_revision)

    def envelope(self):
        return json.loads(self.envelope_json)

    @property
    def episode(self):
        return self.envelope()["episode_id"]

    @property
    def observation_id(self):
        return self.envelope()["observation_id"]

    @property
    def sim_time(self):
        return self.envelope()["sim_time"]

    @property
    def fingerprint(self):
        # An unchanged paused-world snapshot may be re-read, but its capture age
        # still comes from captured_wall and is checked separately.
        return digest([self.envelope_json, self.frame_epoch, self.geometry_revision])


@dataclass(frozen=True)
class Phase:
    id: str
    regime: Regime
    instruction: str
    target_entities: tuple[str, ...]
    max_steps: int
    max_wall_s: float
    max_policy_chunks: int = 0
    entry_checks: tuple[str, ...] = ()
    exit_checks: tuple[str, ...] = ()
    policy_entry: str = "handoff"  # ordinary_start for the unmodified baseline
    native_skill_type: str | None = None

    def __post_init__(self):
        text(self.id, "phase ID", 128)
        text(self.instruction, "instruction", 4096)
        if self.native_skill_type is not None:
            text(self.native_skill_type, "native skill type")
        if not isinstance(self.regime, Regime):
            raise ValueError("Regime enum required")
        identifiers(self.target_entities)
        identifiers(self.entry_checks)
        identifiers(self.exit_checks)
        if self.policy_entry not in {"handoff", "ordinary_start"}:
            raise ValueError("Unknown policy admission mode")
        integer(self.max_steps, minimum=1)
        real(self.max_wall_s, "max_wall_s", .001)
        integer(self.max_policy_chunks)
        if (self.regime == Regime.POLICY) != (self.max_policy_chunks > 0):
            raise ValueError("Only policy phases allocate positive policy chunks")

    def required_checks(self, when):
        if when == "entry":
            common = ("robot_settled",)
            if self.regime == Regime.POLICY:
                common += ("policy_interface",)
                if self.policy_entry == "ordinary_start":
                    common += ("ordinary_start_or_uninterrupted_policy",)
                else:
                    common += ("target_observed", "handoff_envelope")
            else:
                common += ("localization", "collision_world", "trajectory_validated", "payload_model")
            return tuple(dict.fromkeys(common + self.entry_checks))
        if when == "exit":
            common = ("robot_settled",)
            if self.regime != Regime.POLICY:
                common += ("target_reached",)
            return tuple(dict.fromkeys(common + self.exit_checks))
        raise ValueError("entry or exit required")


@dataclass(frozen=True)
class Route:
    id: str
    phases: tuple[Phase, ...]

    def __post_init__(self):
        text(self.id, "route ID")
        if not isinstance(self.phases, tuple) or not 1 <= len(self.phases) <= 16:
            raise ValueError("One to sixteen immutable phases required")
        if not all(isinstance(p, Phase) for p in self.phases):
            raise ValueError("Typed phases required")
        identifiers(tuple(p.id for p in self.phases))


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool | None  # None is UNKNOWN and is never promoted to True.
    evidence: tuple[str, ...]
    note: str = ""

    def __post_init__(self):
        text(self.name)
        if self.passed is not None and type(self.passed) is not bool:
            raise ValueError("Boolean or unknown check required")
        identifiers(self.evidence)
        if not self.evidence:
            raise ValueError("Check must name its evidence")
        if not isinstance(self.note, str) or len(self.note.encode()) > 1024:
            raise ValueError("Bounded check note required")


@dataclass(frozen=True)
class GateReport:
    """Produced by trusted sensor/geometry callbacks, NEVER by the executive.

    Evidence IDs are provenance handles. The private gate provider must resolve
    them against its legal evidence store; their presence alone proves nothing.
    """
    phase_id: str
    when: str
    snapshot_fingerprint: str
    checks: tuple[Check, ...]

    def __post_init__(self):
        text(self.phase_id)
        if self.when not in {"entry", "exit"}:
            raise ValueError("Invalid gate boundary")
        text(self.snapshot_fingerprint)
        if not isinstance(self.checks, tuple) or not all(isinstance(c, Check) for c in self.checks):
            raise ValueError("Immutable typed checks required")
        identifiers(tuple(c.name for c in self.checks))

    def require(self, phase: Phase, when: str, snapshot: Snapshot):
        if (self.phase_id, self.when, self.snapshot_fingerprint) != (
            phase.id, when, snapshot.fingerprint
        ):
            raise PermissionError("Gate result is stale or belongs to another phase")
        values = {c.name: c.passed for c in self.checks}
        bad = tuple(n for n in phase.required_checks(when) if values.get(n) is not True)
        if bad:
            raise PermissionError("Unestablished gates: " + ", ".join(bad))
        # An explicit failing extra gate cannot be hidden by only checking a subset.
        if any(c.passed is not True for c in self.checks):
            raise PermissionError("Additional gate failed or is unknown")


@dataclass(frozen=True)
class ResetRequest:
    episode: str
    execution_epoch: int
    generation: int
    instruction: str
    observation_id: str
    policy_fingerprint: str


@dataclass(frozen=True)
class ResetReceipt:
    request: ResetRequest
    queue_cleared: bool
    history_cleared: bool
    in_flight_drained: bool

    def require(self, request):
        if self.request != request or not all(v is True for v in (
            self.queue_cleared, self.history_cleared, self.in_flight_drained
        )):
            raise PermissionError("Policy handoff reset was not acknowledged")


@dataclass(frozen=True)
class Qualification:
    """Explicit review record. Labels cannot make an unqualified driver safe."""
    id: str
    regime: Regime
    evidence_refs: tuple[str, ...]
    policy_fingerprint: str | None = None
    domain: str = "fixture"  # fixture or behavior_sim, never real hardware in V0

    def __post_init__(self):
        text(self.id)
        identifiers(self.evidence_refs)
        if not self.evidence_refs or not isinstance(self.regime, Regime):
            raise ValueError("Regime and qualification evidence required")
        if self.domain not in {"fixture", "behavior_sim"}:
            raise ValueError("Hybrid V0 supports simulator qualification only")
        if self.regime == Regime.POLICY:
            text(self.policy_fingerprint, "policy fingerprint")
        elif self.policy_fingerprint is not None:
            raise ValueError("Classical qualification must not claim policy weights")
