from __future__ import annotations

import sqlite3

from physical_harness.experiment.fixture import FixtureTransport
from physical_harness.experiment.memory_routing import (
    InformationNeed,
    MemoryTier,
    route_memory_tier,
)
from physical_harness.experiment.validation import dumps, loads

from .test_runner import build


def _records(path, kind):
    with sqlite3.connect(path) as database:
        return [
            loads(row[0])
            for row in database.execute(
                "SELECT body FROM records WHERE kind=? ORDER BY seq", (kind,)
            )
        ]


def test_router_uses_minimum_declared_tier():
    empty = {field: False for field in InformationNeed.__dataclass_fields__}
    assert route_memory_tier(InformationNeed.from_dict(empty)).tier == MemoryTier.CURRENT
    assert route_memory_tier(
        InformationNeed.from_dict(dict(empty, prior_place=True))
    ).tier == MemoryTier.EVENTS
    decision = route_memory_tier(
        InformationNeed.from_dict(
            dict(empty, prior_event=True, visual_motion_comparison=True)
        )
    )
    assert decision.tier == MemoryTier.VISUAL
    assert decision.reasons == ("visual_motion_comparison",)


def test_fixture_freezes_need_before_selected_shadow_retrieval(tmp_path):
    runner, native, transport, journal = build(tmp_path)
    try:
        report = runner.run()
        assert report["harness_finished"]
        routes = _records(tmp_path / "journal.sqlite", "shadow_route")
        packets = _records(tmp_path / "journal.sqlite", "shadow_packet")
        assert len(routes) == len(packets) == report["executive_calls"] == 2
        assert all(route["declared_before_retrieval"] for route in routes)
        assert all(route["selected_tier"] == "M0" for route in routes)
        assert all(packet["cards"] == packet["images"] == [] for packet in packets)
        assert all(
            row["information_need"] == routes[index]["information_need"]
            for index, row in enumerate(runner.loop.trace)
        )
    finally:
        runner.close()
        journal.close()


def test_visual_need_retrieves_m2_only_after_model_response(tmp_path):
    class VisualNeed(FixtureTransport):
        def post(self, path, payload):
            response = super().post(path, payload)
            properties = (
                payload.get("text", {}).get("format", {}).get("schema", {}).get("properties", {})
            )
            if path == "/responses" and "tool" in properties:
                body = loads(response["output"][0]["content"][0]["text"])
                body["information_need"]["visual_identity_continuity"] = True
                response["output"][0]["content"][0]["text"] = dumps(body).decode()
            return response

    transport = VisualNeed()
    runner, native, _, journal = build(tmp_path, transport=transport)
    original = runner.selector.packet

    def after_model_only(*args, **kwargs):
        assert any(
            path == "/responses"
            and "tool"
            in payload.get("text", {}).get("format", {}).get("schema", {}).get("properties", {})
            for path, payload in transport.calls
        )
        return original(*args, **kwargs)

    runner.selector.packet = after_model_only
    try:
        report = runner.run()
        assert report["harness_finished"]
        routes = _records(tmp_path / "journal.sqlite", "shadow_route")
        assert [route["selected_tier"] for route in routes] == ["M2", "M2"]
        assert all(runner.cutoffs.status(route["event_id"]) == "finalized" for route in routes)
    finally:
        runner.close()
        journal.close()
