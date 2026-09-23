from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from physical_harness.core.actions import (
    Basis,
    Intent,
    Verb,
    digest,
    encode,
    ids,
    integer,
    number,
    plain,
    strict_loads,
    text,
)
from physical_harness.core.discovery import FrameRef, immutable_json
from physical_harness.core.tasks import FactPacket
from physical_harness.planning.actions.compiler import Catalog


class ControlMode(str, Enum):
    NAVIGATION = "navigation"
    CARTESIAN = "cartesian"
    JOINT = "joint"
    PRIMITIVE = "parameterized_primitive"
    VISUAL_SERVO = "visual_servo"
    FROZEN_VLA = "frozen_vla"
    GPT_DIRECT = "gpt_direct"
    INSPECT = "inspect"


@dataclass(frozen=True)
class ContextBudget:
    metadata_bytes: int = 20000
    input_tokens: int = 8192  # Used only with an injected model-specific counter.
    images: int = 4
    pixels: int = 4_000_000
    optional_items: int = 24

    def __post_init__(self):
        integer(self.metadata_bytes, low=1024, high=128000)
        integer(self.input_tokens, low=128, high=128000)
        integer(self.images, low=1, high=12)
        integer(self.pixels, low=1, high=16000000)
        integer(self.optional_items, low=0, high=128)


@dataclass(frozen=True)
class ExecutiveOption:
    id: str
    mode: ControlMode
    intent: Intent
    description: str
    candidate_ids: tuple[str, ...]
    required_facts: tuple[str, ...]
    # Strict action IDs remain inside the existing current catalog.

    def __post_init__(self):
        text(self.id)
        if not isinstance(self.mode, ControlMode) or not isinstance(self.intent, Intent):
            raise ValueError("Typed execution mode/intent required")
        text(self.description, limit=800)
        ids(self.candidate_ids, empty=False, limit=32)
        ids(self.required_facts)
        modes = {ControlMode.NAVIGATION: {Verb.NAVIGATE},
                 ControlMode.FROZEN_VLA: {Verb.POLICY},
                 ControlMode.INSPECT: {Verb.INSPECT},
                 ControlMode.GPT_DIRECT: {Verb.STAGE, Verb.RETRACT},
                 ControlMode.VISUAL_SERVO: {Verb.STAGE, Verb.RETRACT},
                 ControlMode.CARTESIAN: {Verb.STAGE, Verb.RETRACT},
                 ControlMode.JOINT: {Verb.STAGE, Verb.RETRACT},
                 ControlMode.PRIMITIVE: set(Verb) - {Verb.POLICY}}
        if self.intent.verb not in modes[self.mode]:
            raise ValueError("Execution mode does not match the physical intent")


@dataclass(frozen=True)
class ContextItem:
    id: str
    kind: str
    json_payload: str
    importance: float = 0.
    mandatory: bool = False

    def __post_init__(self):
        text(self.id)
        if self.kind not in {"focus_entity", "memory", "world_delta", "map", "prior_attempt"}:
            raise ValueError("Unknown context item kind")
        strict_loads(self.json_payload, max_bytes=32000)
        number(self.importance)
        if type(self.mandatory) is not bool:
            raise ValueError("mandatory must be boolean")


@dataclass(frozen=True)
class ExecutivePacket:
    basis: Basis
    task_revision: str
    metadata_json: str
    frames: tuple[FrameRef, ...]
    options: tuple[ExecutiveOption, ...]
    created_wall: float
    omitted_items: tuple[str, ...]
    counted_input_tokens: int | None

    def __post_init__(self):
        if not isinstance(self.basis, Basis):
            raise ValueError("Executive source Basis required")
        text(self.task_revision)
        number(self.created_wall, low=self.basis.captured_wall)
        value = strict_loads(self.metadata_json, max_bytes=128000)
        if (value.get("episode"), value.get("basis"), value.get("task_revision")) != (
            self.basis.episode, self.basis.fingerprint, self.task_revision
        ):
            raise PermissionError("Executive metadata/source mismatch")
        if type(self.frames) is not tuple or not self.frames or any(not isinstance(f, FrameRef) for f in self.frames):
            raise ValueError("Executive images required")
        for frame in self.frames:
            frame.available(self.basis, self.created_wall)
        if type(self.options) is not tuple or any(not isinstance(o, ExecutiveOption) for o in self.options):
            raise ValueError("Typed executive options required")
        ids(tuple(o.id for o in self.options))
        ids(self.omitted_items, limit=256)
        if self.counted_input_tokens is not None:
            integer(self.counted_input_tokens)

    @property
    def fingerprint(self):
        return digest(self)

    def metadata(self):
        return strict_loads(self.metadata_json, max_bytes=128000)


def build_context(*, basis: Basis, task: str, task_revision: str, subtask: str,
                  critical_state: dict, facts: FactPacket, catalog: Catalog,
                  options: tuple[ExecutiveOption, ...], current_images: tuple[FrameRef, ...],
                  historical_images: tuple[FrameRef, ...] = (), items: tuple[ContextItem, ...] = (),
                  now: float, budget: ContextBudget = ContextBudget(), token_counter=None) -> ExecutivePacket:
    """Preserve every control-critical field; prune only explicitly optional items.

    Do not silently drop a constraint, held object, unresolved failure or uncertainty
    to fit a prompt. The existing provider still enforces image/token/spend budgets.
    """
    text(task, limit=4096)
    text(subtask, limit=2048)
    text(task_revision)
    basis.require_same(facts.basis)
    basis.require_same(catalog.basis)
    basis.fresh(now, 2.)
    if type(critical_state) is not dict:
        raise ValueError("Explicit critical state required")
    required = {"held_objects", "constraints", "unresolved_failures", "robot_state"}
    if not required <= set(critical_state):
        raise ValueError("Held objects, constraints, failures and robot state cannot be omitted")
    if type(options) is not tuple or len(options) > 32:
        raise ValueError("Bounded options required")
    ids(tuple(o.id for o in options))
    action_map = {a.id: a for a in catalog.actions}
    for o in options:
        if facts.missing(o.required_facts):
            raise PermissionError("Option missing required current facts")
        for aid in o.candidate_ids:
            if aid not in action_map or not action_map[aid].eligible or action_map[aid].program.proposal.intent != o.intent:
                raise PermissionError("Option does not resolve to eligible intent-matched candidates")
    if type(current_images) is not tuple or not current_images:
        raise ValueError("At least one current RGB view required")
    frames = current_images + historical_images
    if len(frames) > budget.images or sum(f.pixels for f in frames) > budget.pixels:
        raise ValueError("Image budget exceeded; select fewer images explicitly")
    ids(tuple(f.asset_id for f in frames))
    for f in current_images:
        basis.require_same(f.basis)
        f.available(basis, now)
    for f in historical_images:
        f.available(basis, now)
    meta = {"episode": basis.episode, "task": task, "task_revision": task_revision,
            "subtask": subtask, "basis": basis.fingerprint,
            "critical_state": plain(critical_state), "current_facts": plain(facts.facts),
            "options": plain(options), "catalog_id": catalog.id,
            "images": [{"id": f.asset_id, "role": "current" if f in current_images else "historical",
                        "observed_sim": f.basis.sim_time, "available_wall": f.available_wall,
                        "sha256": f.content_sha256} for f in frames],
            "items": [], "omitted_items": []}
    if type(items) is not tuple or len(items) > 256:
        raise ValueError("Bounded context candidates required")
    ids(tuple(i.id for i in items), limit=256)
    ordered = sorted(items, key=lambda i: (not i.mandatory, -i.importance, i.id))
    for item in ordered:
        addition = {"id": item.id, "kind": item.kind, "data": strict_loads(item.json_payload)}
        meta["items"].append(addition)
        over = len(encode(meta)) > budget.metadata_bytes or (
            not item.mandatory and len(meta["items"]) > budget.optional_items + sum(i.mandatory for i in ordered))
        if over:
            if item.mandatory:
                raise ValueError("Critical context cannot fit; do not truncate it")
            meta["items"].pop()
            meta["omitted_items"].append(item.id)
    if len(encode(meta)) > budget.metadata_bytes:
        raise ValueError("Required context/candidate catalog exceeds budget")
    count = None
    if token_counter is not None:
        count = token_counter(meta, frames)
        integer(count)
        if count > budget.input_tokens:
            raise ValueError("Model-specific input token budget exceeded")
    return ExecutivePacket(basis, task_revision, immutable_json(meta, max_bytes=budget.metadata_bytes),
                           frames, options, now, tuple(meta["omitted_items"]), count)
