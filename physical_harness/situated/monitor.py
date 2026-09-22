"""Causal progress monitoring with abstention and optional learned observations.

A learned 'complete' is a proposal, not task truth. This does not replace the
independent verifier or controller-rate safety monitors.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..action_compiler.types import Basis, digest, ids, integer, plain, strict_loads, text
from .visual import MonitorPacket


@dataclass(frozen=True)
class MonitorVerdict:
    packet_fingerprint: str
    status: str
    cited_asset_ids: tuple[str, ...]
    source: str
    source_revision: str

    def __post_init__(self):
        text(self.packet_fingerprint)
        text(self.source)
        text(self.source_revision)
        if self.status not in {"progress", "complete", "unknown", "target_lost", "failed"}:
            raise ValueError("Unsupported monitor status")
        ids(self.cited_asset_ids, empty=False)

    def require(self, packet: MonitorPacket):
        if self.packet_fingerprint != packet.fingerprint:
            raise PermissionError("Monitor reply belongs to a different command/window")
        if not set(self.cited_asset_ids) <= set(packet.observed_ids):
            raise PermissionError("Only observed recent evidence can support a monitor verdict")
        current_ids = {packet.recent[-1].asset_id}
        if packet.wrist is not None:
            current_ids.add(packet.wrist.asset_id)
        if not set(self.cited_asset_ids) & current_ids:
            raise PermissionError("Monitor verdict must cite current evidence")


def parse_monitor_reply(reply, packet: MonitorPacket, *, source: str, revision: str) -> MonitorVerdict:
    from ..action_compiler.types import encode
    raw = strict_loads(encode(reply) if isinstance(reply, dict) else reply, max_bytes=8192)
    if set(raw) != {"packet_fingerprint", "status", "cited_asset_ids"}:
        raise ValueError("Unexpected monitor fields")
    if type(raw["cited_asset_ids"]) is not list:
        raise ValueError("Citation list required")
    result = MonitorVerdict(raw["packet_fingerprint"], raw["status"], tuple(raw["cited_asset_ids"]),
                            source, revision)
    result.require(packet)
    return result


def monitor_context(packet: MonitorPacket) -> dict:
    return {"packet_fingerprint": packet.fingerprint, "command_id": packet.command_id,
            "goal": plain(packet.goal), "recent": plain(packet.recent),
            "command_anchor": plain(packet.anchor), "current_wrist": plain(packet.wrist),
            "instruction": "Judge this command from current observations, not elapsed time. "
            "References are desired/historical, not proof of the outcome. Use unknown when "
            "the decisive property is not observable. Cite current observed assets only."}


@dataclass(frozen=True)
class MonitorSignal:
    event_id: str
    command_id: str
    basis: Basis
    event_type: str
    status: str
    evidence_ids: tuple[str, ...]
    semantic_authority: str = "advisory_only"


class ProgressMonitor:
    def __init__(self, *, journal, confirmation_windows=2, qualified_revision: str | None = None,
                 independently_confirm=None):
        integer(confirmation_windows, low=1, high=10)
        if qualified_revision is not None and not callable(independently_confirm):
            raise ValueError("Promotion requires an independent qualified completion check")
        self.journal, self.windows = journal, confirmation_windows
        self.revision, self.confirm = qualified_revision, independently_confirm
        self._last = {}
        self._count = {}
        self._seen = set()
        # Recovery rebuilds debounce only from durable records, not cached Python state.
        for r in journal.records("situated_monitor"):
            self._seen.add(r["packet_fingerprint"])
            k = (r["command_id"], r["goal_id"])
            self._last[k] = r["sim_time"]
            self._count[k] = r["complete_streak"]

    def accept(self, packet: MonitorPacket, verdict: MonitorVerdict) -> MonitorSignal:
        verdict.require(packet)
        if packet.current.episode != self.journal.episode:
            raise PermissionError("Foreign monitor episode")
        if packet.fingerprint in self._seen:
            raise PermissionError("Repeated window is not independent evidence")
        key = packet.command_id, packet.goal.id
        if packet.current.sim_time <= self._last.get(key, -1):
            raise PermissionError("Monitor evidence did not advance")
        count = self._count.get(key, 0)+1 if verdict.status == "complete" else 0
        promoted = False
        if verdict.status == "complete" and count >= self.windows and self.revision is not None:
            promoted = (verdict.source_revision == self.revision and
                        self.confirm(packet, verdict) is True)
        event = {"progress": "local_progress", "unknown": "verifier_uncertain",
                 "target_lost": "target_lost", "failed": "skill_failed",
                 "complete": "subgoal_complete" if promoted else "completion_candidate"}[verdict.status]
        event_id = "monitor:" + digest([packet.fingerprint, verdict])[:24]
        row = {"packet_fingerprint": packet.fingerprint, "command_id": packet.command_id,
               "goal_id": packet.goal.id, "sim_time": packet.current.sim_time,
               "complete_streak": count, "verdict": plain(verdict), "promoted": promoted,
               "event_type": event, "semantic_authority": "advisory_only"}
        self.journal.put("situated_monitor", event_id, row)
        self._seen.add(packet.fingerprint)
        self._last[key], self._count[key] = packet.current.sim_time, count
        return MonitorSignal(event_id, packet.command_id, packet.current, event, verdict.status,
                             verdict.cited_asset_ids)
