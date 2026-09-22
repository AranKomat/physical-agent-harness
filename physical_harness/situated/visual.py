"""Visual memory, desired outcome, and information-seeking goals stay distinct."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..action_compiler.types import Basis, digest, ids, integer, number, text
from .contracts import same_episode


class VisualRole(str, Enum):
    OBSERVATION = "observation"
    COMMAND_ANCHOR = "command_anchor"
    OUTCOME_REFERENCE = "outcome_reference"
    HYPOTHETICAL_OUTCOME = "hypothetical_outcome"


@dataclass(frozen=True)
class VisualAsset:
    """Reference into the EXISTING evidence/media store. No pixels persisted here.

    observed_at may predate availability (e.g. a delayed annotation). Causal
    filtering uses BOTH times. Generated/reference images cannot certify reality.
    """
    asset_id: str
    episode: str
    role: VisualRole
    camera: str
    observed_at: float
    available_at: float
    sha256: str
    evidence_ids: tuple[str, ...]
    command_id: str | None = None

    def __post_init__(self):
        for s in (self.asset_id, self.episode, self.camera):
            text(s)
        if not isinstance(self.role, VisualRole):
            raise ValueError("Explicit visual role required")
        number(self.observed_at, low=0)
        number(self.available_at, low=self.observed_at)
        if len(self.sha256) != 64 or any(c not in "0123456789abcdef" for c in self.sha256):
            raise ValueError("Content SHA-256 required")
        ids(self.evidence_ids, empty=False)
        if self.command_id is not None:
            text(self.command_id)
        if self.role == VisualRole.COMMAND_ANCHOR and self.command_id is None:
            raise ValueError("Command anchor must identify its command instance")

    def require_available(self, basis: Basis):
        if self.episode != basis.episode or self.available_at > basis.sim_time:
            raise PermissionError("Future/foreign visual reference")

    @property
    def fingerprint(self):
        return digest(self)


@dataclass(frozen=True)
class ReferenceGrant:
    """Operator-approved import of a demonstration/goal, never a current observation."""
    asset_sha256: str
    source_episode: str
    target_episode: str
    review_id: str
    available_at: float

    def __post_init__(self):
        for s in (self.asset_sha256, self.source_episode, self.target_episode, self.review_id):
            text(s)
        number(self.available_at, low=0)


class GoalKind(str, Enum):
    OUTCOME = "outcome"
    INFORMATION = "information"


@dataclass(frozen=True)
class VisualGoal:
    id: str
    kind: GoalKind
    entity: str
    property: str
    criterion: str
    references: tuple[VisualAsset, ...] = ()
    reference_grants: tuple[ReferenceGrant, ...] = ()

    def __post_init__(self):
        for s in (self.id, self.entity, self.property, self.criterion):
            text(s, limit=2048)
        if not isinstance(self.kind, GoalKind) or type(self.references) is not tuple:
            raise ValueError("Typed goal/references required")
        if len(self.references) > 4 or any(not isinstance(x, VisualAsset) for x in self.references):
            raise ValueError("At most four visual reference assets")
        ids(tuple(x.asset_id for x in self.references))
        if type(self.reference_grants) is not tuple or len(self.reference_grants) > 4 or any(
            not isinstance(g, ReferenceGrant) for g in self.reference_grants
        ):
            raise ValueError("Bounded explicit reference grants required")

    def check_references(self, current: Basis):
        for ref in self.references:
            if ref.episode == current.episode:
                ref.require_available(current)
                continue
            if ref.role not in {VisualRole.OUTCOME_REFERENCE, VisualRole.HYPOTHETICAL_OUTCOME}:
                raise PermissionError("Foreign imagery must be explicitly labeled as an outcome reference")
            granted = any((g.asset_sha256, g.source_episode, g.target_episode) ==
                          (ref.sha256, ref.episode, current.episode) and g.available_at <= current.sim_time
                          for g in self.reference_grants)
            if not granted:
                raise PermissionError("No causal authorization for external demonstration reference")


@dataclass(frozen=True)
class ObservationFrame:
    basis: Basis
    front: VisualAsset
    wrist: VisualAsset | None = None

    def __post_init__(self):
        if not isinstance(self.basis, Basis):
            raise ValueError("Basis required")
        for asset in (self.front, self.wrist):
            if asset is None:
                continue
            if not isinstance(asset, VisualAsset) or asset.role != VisualRole.OBSERVATION:
                raise ValueError("Current frame cannot be a goal or generated image")
            asset.require_available(self.basis)
            if asset.observed_at != self.basis.sim_time:
                raise ValueError("Frame capture/evidence clock mismatch")


@dataclass(frozen=True)
class MonitorPacket:
    command_id: str
    goal: VisualGoal
    current: Basis
    recent: tuple[VisualAsset, ...]
    anchor: VisualAsset
    wrist: VisualAsset | None

    def __post_init__(self):
        text(self.command_id)
        if not isinstance(self.current, Basis) or not isinstance(self.goal, VisualGoal):
            raise ValueError("Typed monitor basis/goal required")
        self.goal.check_references(self.current)
        if self.anchor.role != VisualRole.COMMAND_ANCHOR or self.anchor.command_id != self.command_id:
            raise PermissionError("Wrong command anchor")
        self.anchor.require_available(self.current)
        if type(self.recent) is not tuple or not 1 <= len(self.recent) <= 16:
            raise ValueError("Bounded causal monitor window required")
        ids(tuple(a.asset_id for a in self.recent))
        previous = -1.
        for asset in self.recent:
            if asset.role != VisualRole.OBSERVATION:
                raise PermissionError("Recent evidence cannot be a target/hypothetical image")
            asset.require_available(self.current)
            if asset.observed_at <= previous or asset.observed_at < self.anchor.observed_at:
                raise PermissionError("Noncausal monitor history")
            previous = asset.observed_at
        if self.recent[-1].observed_at != self.current.sim_time:
            raise PermissionError("Monitor window must end at current capture")
        if self.wrist:
            if self.wrist.role != VisualRole.OBSERVATION or self.wrist.observed_at != self.current.sim_time:
                raise PermissionError("Wrist must be a current observation")
            self.wrist.require_available(self.current)

    @property
    def fingerprint(self):
        return digest(self)

    @property
    def observed_ids(self):
        return tuple(a.asset_id for a in self.recent) + ((self.wrist.asset_id,) if self.wrist else ())


def monitor_packet(*, command_id: str, goal: VisualGoal, frames: tuple[ObservationFrame, ...],
                   anchor: VisualAsset, count: int = 8, stride: int = 3) -> MonitorPacket:
    """Use causal recorded frames; never pad duplicates into independent evidence."""
    text(command_id)
    integer(count, low=1, high=16)
    integer(stride, low=1, high=60)
    if type(frames) is not tuple or not frames or len(frames) > 4096:
        raise ValueError("Bounded nonempty chronological frames required")
    if any(not isinstance(f, ObservationFrame) for f in frames):
        raise ValueError("Typed frames required")
    current = frames[-1].basis
    if anchor.role != VisualRole.COMMAND_ANCHOR or anchor.command_id != command_id:
        raise PermissionError("Wrong command-start reference")
    anchor.require_available(current)
    goal.check_references(current)
    for i, f in enumerate(frames):
        f.front.require_available(current)
        if f.basis.sim_time < anchor.observed_at:
            raise PermissionError("Recent history predates this command")
        if i:
            same_episode(frames[i-1].basis, f.basis)
            frames[i-1].basis.require_continuity(f.basis)
            if f.basis.sim_time <= frames[i-1].basis.sim_time:
                raise ValueError("Distinct increasing recent captures required")
    indices = sorted(range(len(frames)-1, max(-1, len(frames)-1-count*stride), -stride))
    recent = tuple(frames[i].front for i in indices)
    ids(tuple(a.asset_id for a in recent))
    return MonitorPacket(command_id, goal, current, recent, anchor, frames[-1].wrist)
