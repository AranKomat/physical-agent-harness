from __future__ import annotations

from dataclasses import dataclass

import pytest

from physical_harness.reasoning.context.rich import (
    BroadMemorySelector,
    CoverageNote,
    RichContextBuilder,
    RichContextPolicy,
    attach_rich_memory,
)
from physical_harness.world.memory.schemas import Asset, Card
from physical_harness.world.memory.store import MemoryStore
from physical_harness.world.state import ContextBudgetExceeded
from physical_harness.world.topology import PlaceEdge, PlaceNode, TopologicalMap


class FakeState:
    episode = "ep"

    def __init__(self):
        self._hist = {
            "ball_1": [
                dict(subject="ball_1", predicate="location", object='{"place":"hallway"}',
                     sim_time=1.0, valid_until=5.0, evidence_id="e1", epistemic="observed"),
                dict(subject="ball_1", predicate="location", object='{"place":"kitchen"}',
                     sim_time=5.0, valid_until=None, evidence_id="e5", epistemic="observed"),
            ],
            "ball_2": [
                dict(subject="ball_2", predicate="visibility", object="not_observed",
                     sim_time=7.0, valid_until=None, evidence_id="e7", epistemic="inferred"),
            ],
        }

    def subjects(self):
        return ("ball_1", "ball_2", "table_1")

    def history(self, subject):
        return list(self._hist.get(subject, []))

    def project(self, goal, subjects, image_evidence, *, max_images, max_events, max_bytes):
        beliefs = [
            dict(subject="ball_1", predicate="label", object="tennis ball", sim_time=5.0,
                 evidence_id="e5", epistemic="observed"),
            dict(subject="ball_1", predicate="location", object='{"place":"kitchen","support":"table_1"}',
                 sim_time=5.0, evidence_id="e5", epistemic="observed"),
            dict(subject="ball_1", predicate="visibility", object="visible", sim_time=5.0,
                 evidence_id="e5", epistemic="observed"),
            dict(subject="ball_2", predicate="label", object="tennis ball", sim_time=7.0,
                 evidence_id="e7", epistemic="observed"),
            dict(subject="ball_2", predicate="visibility", object="not_observed", sim_time=7.0,
                 evidence_id="e7", epistemic="inferred"),
            dict(subject="ball_2", predicate="identity_candidates", object='["ball_2","ball_4"]',
                 sim_time=7.0, evidence_id="e7", epistemic="observed"),
            dict(subject="table_1", predicate="label", object="kitchen table", sim_time=5.0,
                 evidence_id="e5", epistemic="observed"),
        ]
        beliefs = [b for b in beliefs if b["subject"] in set(subjects)]
        return {
            "episode": "ep",
            "goal": goal,
            "beliefs": beliefs,
            "task_ledger": [{"id":"put_ball","goal":"IN(ball_1,basket)","status":"planned",
                             "evidence_id":None,"dependencies":[],"evidence":[]}],
            "images": [{"id": i, "uri": f"{i}.png", "sim_time": 8.0} for i in image_evidence],
            "recent_events": [{"seq": 1, "sim_time": 7.0, "type": "belief_updated"}],
            "memory_notice": "fixture",
        }


@dataclass(frozen=True)
class Event:
    type: str
    sim_time: float
    payload: dict
    event_id: str


def test_rich_context_keeps_broad_roster_history_and_runtime_events():
    state = FakeState()
    graph = TopologicalMap()
    graph.upsert_node(PlaceNode("kitchen", "Kitchen", "room"))
    graph.upsert_node(PlaceNode("hall", "Hallway", "corridor"))
    graph.add_edge(PlaceEdge("kitchen", "hall", gateway_entity="door_7"))
    graph.update_gateway("door_7", "open", ("door-image",))
    builder = RichContextBuilder(state)
    result = builder.build(
        goal="put away the balls",
        focus_entities=("ball_1",),
        image_evidence=["now"],
        runtime_events=[
            Event("skill_failed", 7.5, {"skill_id":"pick-1","reason":"collision","secret":{"x":1}}, "r1")
        ],
        topology=graph,
        current_place="kitchen",
        observation_coverage=[
            CoverageNote("hall_floor", 7.0, "high", "not_seen", ("e7",),
                         "ball_2 was not detected during a broad rescan")
        ],
    )
    assert [x["id"] for x in result["entity_roster"]] == ["ball_1","ball_2","table_1"]
    ambiguous = next(x for x in result["entity_roster"] if x["id"] == "ball_2")
    assert ambiguous["identity_candidates"] == ["ball_2","ball_4"]
    assert "visibility" in ambiguous["inferred_fields"]
    assert result["entity_history"]["ball_1"][-1]["value"]["place"] == "kitchen"
    assert result["runtime_events"][0]["details"] == {
        "skill_id":"pick-1","reason":"collision"
    }
    assert result["topology"]["current_place"] == "kitchen"
    assert result["observation_coverage"][0]["result"] == "not_seen"


def test_focus_is_retained_even_if_roster_omits_it():
    result = RichContextBuilder(FakeState()).build(
        goal="g", focus_entities=("ball_1",), roster_entities=("table_1",), image_evidence=[]
    )
    assert set(x["id"] for x in result["entity_roster"]) == {"ball_1","table_1"}
    assert "ball_1" in result["current_focus"]


def test_roster_limit_fails_instead_of_silent_pruning():
    policy = RichContextPolicy(max_roster_entities=1)
    with pytest.raises(ContextBudgetExceeded):
        RichContextBuilder(FakeState(), policy).build(
            goal="g", focus_entities=("ball_1",), roster_entities=("ball_1","ball_2"),
            image_evidence=[]
        )


def test_coverage_validation():
    with pytest.raises(ValueError):
        CoverageNote("table", 1.0, "perfect", "not_seen")


def test_context_budget_fails_visibly():
    policy = RichContextPolicy(max_metadata_bytes=100)
    with pytest.raises(ContextBudgetExceeded):
        RichContextBuilder(FakeState(), policy).build(
            goal="g", focus_entities=("ball_1",), image_evidence=[]
        )


def test_zero_history_and_runtime_budgets_keep_nothing():
    policy = RichContextPolicy(
        history_items_per_predicate=0,
        max_runtime_events=0,
    )
    result = RichContextBuilder(FakeState(), policy).build(
        goal="g",
        focus_entities=("ball_1",),
        image_evidence=[],
        runtime_events=[Event("skill_failed", 7.5, {}, "r1")],
    )
    assert result["entity_history"]["ball_1"] == []
    assert result["runtime_events"] == []


def test_topology_limit_fails_visibly():
    graph = TopologicalMap()
    graph.upsert_node(PlaceNode("a","A","room"))
    graph.upsert_node(PlaceNode("b","B","room"))
    policy = RichContextPolicy(max_topology_places=1)
    with pytest.raises(ContextBudgetExceeded):
        RichContextBuilder(FakeState(), policy).build(
            goal="g", focus_entities=(), image_evidence=[], topology=graph
        )


def _blob_reader(blobs):
    def read(name):
        return blobs[name]
    return read


def _asset(ep, aid, t, blob):
    import hashlib
    digest = hashlib.sha256(blob).hexdigest()
    return Asset(aid, ep, "image", digest+".jpg", digest, t, t, f"o-{aid}", "head", 10, 10)


def test_broad_memory_selector_unions_entity_place_goal_and_recent(tmp_path):
    blobs = {}
    # Create content-addressed blobs before constructing the store.
    for name, data in [("a", b"a"),("b", b"b"),("c", b"c"),("d", b"d")]:
        import hashlib
        blobs[hashlib.sha256(data).hexdigest()+".jpg"] = data
    store = MemoryStore(tmp_path/"m.sqlite", "ep", _blob_reader(blobs))
    for name, data, t in [("a", b"a", 1), ("b", b"b", 2), ("c", b"c", 3), ("d", b"d", 4)]:
        asset = _asset("ep", name, t, data)
        store.add_asset(asset)
    cards = [
        Card("c1","ep","event","e1","skill_failed",1,1,("a",),("ball_1",),("hall",),
             "failed pick ball_1","failed"),
        Card("c2","ep","place_view","e2","place_entered",2,2,("b",),(),("kitchen",),
             "entered kitchen","not_assessed"),
        Card("c3","ep","event","e3","world_changed",3,3,("c",),("ball_2",),("kitchen",),
             "ball moved toward basket","not_assessed"),
        Card("c4","ep","event","e4","decision_required",4,4,("d",),(),(),
             "recent event","not_assessed"),
    ]
    for card in cards:
        store.add_card(card)
    selector = BroadMemorySelector(store, RichContextPolicy(memory_max_cards=20))
    packet = selector.packet(
        store.cutoff(4), goal="ball basket", focus_entities=("ball_1",), current_place="kitchen"
    )
    ids = {c["card_id"] for c in packet["cards"]}
    assert {"c1","c2","c3","c4"} <= ids
    assert packet["cards"][0]["card_id"] == "c3"
    assert "focus_entity:ball_1" in packet["selection_reasons"]["c1"]
    assert "current_place:kitchen" in packet["selection_reasons"]["c2"]
    store.close()


def test_attach_rich_memory_enforces_combined_limits():
    base = {"episode": "ep", "current_images": [{"id": "now"}]}
    packet = {
        "cutoff": {"episode_id": "ep"},
        "cards": [],
        "images": [{"asset_id": "old"}],
    }
    result = attach_rich_memory(base, packet, provider_check=lambda _: True)
    assert result["episodic_memory"]["images"][0]["asset_id"] == "old"

    with pytest.raises(ContextBudgetExceeded):
        attach_rich_memory(
            base,
            packet,
            policy=RichContextPolicy(max_combined_images=1),
        )
    with pytest.raises(ValueError, match="episode mismatch"):
        attach_rich_memory({"episode": "other", "current_images": []}, packet)
