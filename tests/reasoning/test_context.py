import json

import pytest

from physical_harness.reasoning.context.conservative import ContextPolicy, ContextProjector
from physical_harness.world.state import ContextBudgetExceeded, WorldState


@pytest.fixture
def state():
    with WorldState(":memory:", "ep") as state:
        yield state


def build(state, **kwargs):
    return ContextProjector(state).build(
        goal="goal", relevant_entities=[], image_evidence=[], **kwargs
    )


def test_no_trace_scorer_or_arbitrary_metadata_leakage(state):
    state.add_evidence("e", 1, "perception", "frame.png", {"native_score": "SECRET_PAYLOAD"})
    state.record_command("cmd", 1, {"transcript": "SECRET_COMMAND", "scorer": 1})
    result = build(
        state,
        navigation_summary={
            "status": "blocked",
            "transcript": "SECRET_TRACE",
            "metadata": {"score": "SECRET_META"},
        },
        executor_summary={
            "skill_id": "s",
            "native_score": "SECRET_SCORE",
            "history": ["SECRET_HISTORY"],
        },
    )
    assert "SECRET" not in json.dumps(result)
    assert result["navigation"] == {"status": "blocked"}
    assert result["executors"] == {"skill_id": "s"}


def test_final_budget_includes_summaries_and_envelope(state):
    payload = build(
        state, navigation_summary={"status": "ready"}, executor_summary={"skill_id": "s"}
    )
    size = len(json.dumps(payload, sort_keys=True, allow_nan=False).encode("utf-8"))
    for budget, passes in [(size, True), (size - 1, False)]:
        projector = ContextProjector(state, ContextPolicy(max_bytes=budget))
        args = dict(
            goal="goal",
            relevant_entities=[],
            image_evidence=[],
            navigation_summary={"status": "ready"},
            executor_summary={"skill_id": "s"},
        )
        if passes:
            assert projector.build(**args) == payload
        else:
            with pytest.raises(ContextBudgetExceeded):
                projector.build(**args)
    with pytest.raises(ContextBudgetExceeded):
        build(state, executor_summary={"skill_id": "x" * 12000})


def test_image_event_bounds_and_episode_scope(state):
    for i in range(6):
        state.add_evidence(str(i), i, "perception", str(i) + ".png")
    payload = build(state)
    assert len(payload["recent_events"]) == 5
    with pytest.raises(ContextBudgetExceeded):
        state.project("goal", [], [str(i) for i in range(5)])
    with pytest.raises(ValueError):
        state.project("goal", [], ["other-episode"])
    with pytest.raises(ValueError):
        build(state, navigation_summary={"distance_remaining_m": float("nan")})
