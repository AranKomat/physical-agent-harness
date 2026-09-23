from dataclasses import replace

import pytest

from experiments.fixtures.handoff import FixtureWorld
from physical_harness.execution.handoff.contracts import Qualification, Regime
from physical_harness.execution.handoff.executor import HybridExecutor
from physical_harness.execution.handoff.integration import (
    ablation_routes,
    journal_sink,
    wrap_native,
)
from physical_harness.integrations.experiment.journal import Journal
from physical_harness.integrations.experiment.native import NativeBindings as Binding


def test_native_wrapper_preserves_observer_and_never_mutates_original():
    w = FixtureWorld()
    h = w.executor()
    original = Binding("native", w.snapshot, w.learned, w.stop, qualification_id="fixture")
    wrapped = wrap_native(original, h, domain="fixture")
    assert wrapped.observe == original.observe
    assert wrapped.run_skill == h.run_skill
    assert original.run_skill == w.learned
    assert wrapped.stop == h.stop


@pytest.mark.parametrize("kwargs", [dict(simulated=False), dict(simulated=1), dict(qualification_id=None)])
def test_native_wrapper_rejects_unqualified_or_physical_binding(kwargs):
    w = FixtureWorld()
    n = Binding("native", w.snapshot, w.learned, w.stop, qualification_id="fixture")
    with pytest.raises(PermissionError):
        wrap_native(replace(n, **kwargs), w.executor(), domain="fixture")


def test_journal_sink_uses_existing_put_contract():
    rows = []
    class Journal:
        def put(self, kind, id, payload):
            rows.append((kind, id, payload))
    emit = journal_sink(Journal())
    emit("reserved", {"x": 1})
    emit("phase_end", {"x": 2})
    assert rows[0][0] == "hybrid"
    assert rows[0][1] != rows[1][1]


def test_journal_sink_recreation_preserves_events_across_reopen(tmp_path):
    path = tmp_path / "journal.sqlite"
    for value in (1, 2):
        journal = Journal(path, "fixture", max_calls=1, max_microusd=1)
        try:
            journal_sink(journal)("reserved", {"value": value})
        finally:
            journal.close()
    journal = Journal(path, "fixture", max_calls=1, max_microusd=1)
    try:
        rows = journal.records("hybrid")
        assert [r["payload"]["value"] for r in rows] == [1, 2]
        assert rows[0]["id"] != rows[1]["id"]
    finally:
        journal.close()


def test_ablation_routes_equal_total_ceiling_preserve_policy_instruction():
    routes = ablation_routes(target="radio", policy_instruction="turn on the radio")
    for route in routes.values():
        assert sum(p.max_steps for p in route.phases) == 3224
        policy = [p for p in route.phases if p.regime == Regime.POLICY]
        assert len(policy) == 1 and policy[0].instruction == "turn on the radio"
    assert [p.regime for p in routes["A"].phases] == [Regime.POLICY]
    assert "safe_release_or_stable_payload" in routes["D"].phases[-1].entry_checks


def test_bad_ablation_budget_fails_before_any_driver_load():
    with pytest.raises(ValueError):
        ablation_routes(target="radio", policy_instruction="turn on radio", total_steps=10)


def test_fixture_records_cannot_authorize_behavior_simulation():
    w = FixtureWorld()
    old = w.executor()
    with pytest.raises(ValueError, match="Fixture"):
        HybridExecutor(episode="fixture", routes=old.routes, backends=old.backends,
                       observe=w.snapshot, stop=w.stop, policy=w.policy, emit=lambda *a: None,
                       domain="behavior_sim")


def test_policy_qualification_requires_exact_pinned_identity():
    w = FixtureWorld()
    old = w.executor()
    bad = dict(old.backends)
    bad[Regime.POLICY] = replace(bad[Regime.POLICY], qualification=Qualification(
        "bad", Regime.POLICY, ("e",), "another-checkpoint"))
    with pytest.raises(ValueError, match="pinned"):
        HybridExecutor(episode="fixture", routes=old.routes, backends=bad,
                       observe=w.snapshot, stop=w.stop, policy=w.policy, emit=lambda *a: None)


def test_default_native_wrapper_rejects_fixture_as_behavior_driver():
    w = FixtureWorld()
    n = Binding("native", w.snapshot, w.learned, w.stop, qualification_id="q")
    with pytest.raises(PermissionError, match="domain"):
        wrap_native(n, w.executor())
