"""Current context snapshots preserve per-field age and freeze M0 before model work."""
from __future__ import annotations

from physical_harness.integrations.experiment.validation import dumps, number
from physical_harness.reasoning.context import project_context
from physical_harness.reasoning.context.rich import RichContextPolicy
from physical_harness.world.state import ContextBudgetExceeded


class ExperimentContext:
    def __init__(self, world, policy: RichContextPolicy | None = None):
        self.world = world
        self.policy = policy or RichContextPolicy()

    def build(self, *, now: float, **kwargs) -> dict:
        now = number(now)
        result = project_context("rich", state=self.world, policy=self.policy, **kwargs)
        result["observed_through"] = now
        # A recently updated visibility flag must not freshen a 5-minute-old location.
        result["field_provenance"] = {}
        for entity in result["entity_roster"]:
            provenance = {}
            for row in self.world.db.execute(
                "SELECT predicate,sim_time,evidence_id,epistemic FROM beliefs "
                "WHERE episode=? AND subject=? AND valid_until IS NULL ORDER BY predicate",
                (self.world.episode, entity["id"])):
                if row["sim_time"] > now:
                    raise ValueError("Current world contains future evidence")
                provenance[row["predicate"]] = dict(row, age_s=now - row["sim_time"])
            result["field_provenance"][entity["id"]] = provenance
        # Explicit contradictions stay visible even when the old belief is retained.
        conflicts = []
        from physical_harness.integrations.experiment.validation import loads
        for row in self.world.db.execute(
            "SELECT seq,sim_time,payload FROM events WHERE episode=? AND type='belief_conflict'",
            (self.world.episode,)):
            p = loads(row["payload"])
            current = self.world.belief(p["subject"], p["predicate"])
            if current and current["sim_time"] <= row["sim_time"] <= now:
                conflicts.append({"at": row["sim_time"], "subject": p["subject"],
                                  "predicate": p["predicate"], "old": p.get("old"),
                                  "new": p.get("new"), "evidence": p.get("evidence")})
        result["unresolved_belief_conflicts"] = conflicts
        result["epistemic_notice"] = (
            "Last-update is not last-confirmed-location. Per-field provenance carries age. "
            "Not observed is not absent. Indistinguishable objects may have unresolved identity. "
            "A record of a commanded move is not evidence that the move succeeded.")
        if len(dumps(result)) > self.policy.max_metadata_bytes:
            raise ContextBudgetExceeded("Provenance-inclusive context exceeds experiment budget")
        return result
