"""Readable example of the v0.9 broad context shape.

This is synthetic and performs no model or robot calls.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from physical_harness.reasoning.context.rich import CoverageNote, RichContextBuilder
from physical_harness.world.topology import PlaceEdge, PlaceNode, TopologicalMap


class ExampleState:
    episode = "halloween-demo"

    def subjects(self):
        return ("robot","candle_1","candle_2","pumpkin_1","cabinet_A","coffee_table")

    def history(self, subject):
        histories = {
            "candle_2": [
                {"subject":"candle_2","predicate":"location","object":'{"place":"living_room","support":"coffee_table"}',
                 "sim_time":3.4,"valid_until":63.0,"evidence_id":"img-014","epistemic":"observed"},
                {"subject":"candle_2","predicate":"visibility","object":"not_observed",
                 "sim_time":63.0,"valid_until":None,"evidence_id":"img-254","epistemic":"inferred"},
            ]
        }
        return histories.get(subject, [])

    def project(self, goal, subjects, image_evidence, *, max_images, max_events, max_bytes):
        rows = [
            ("robot","place","living_room",70.0,"pose-70","observed"),
            ("candle_1","label","orange candle with bat pattern",40.0,"crop-1","observed"),
            ("candle_1","IN","cabinet_A",40.0,"img-169","observed"),
            ("candle_1","visibility","not_observed",41.0,"img-171","inferred"),
            ("candle_2","label","tall orange candle with black stripe",63.0,"crop-2","observed"),
            ("candle_2","location",'{"place":"living_room","support":"coffee_table"}',63.0,"img-254","observed"),
            ("candle_2","visibility","visible",70.0,"img-272","observed"),
            ("pumpkin_1","label","small plastic jack-o-lantern",3.4,"crop-p","observed"),
            ("pumpkin_1","location",'{"place":"living_room","support":"side_table"}',3.4,"img-014","observed"),
            ("cabinet_A","open_state","open",12.0,"img-047","observed"),
            ("coffee_table","label","glass coffee table",3.4,"img-014","observed"),
        ]
        allowed=set(subjects)
        beliefs=[{"subject":s,"predicate":p,"object":o,"sim_time":t,"evidence_id":e,"epistemic":epi}
                 for s,p,o,t,e,epi in rows if s in allowed]
        return {
            "episode":self.episode,"goal":goal,"beliefs":beliefs,
            "task_ledger":[
                {"id":"c1","goal":"IN(candle_1,cabinet_A)","status":"observed_complete","evidence_id":"img-169","dependencies":[],"evidence":["img-169"]},
                {"id":"c2","goal":"IN(candle_2,cabinet_A)","status":"planned","evidence_id":None,"dependencies":[],"evidence":[]},
                {"id":"p1","goal":"IN(pumpkin_1,cabinet_A)","status":"planned","evidence_id":None,"dependencies":[],"evidence":[]},
            ],
            "images":[{"id":x,"uri":x+".png","sim_time":70.0} for x in image_evidence],
            "recent_events":[{"seq":98,"sim_time":63.0,"type":"belief_updated"}],
            "memory_notice":"Beliefs are fallible."
        }


@dataclass(frozen=True)
class Event:
    type: str
    sim_time: float
    payload: dict
    event_id: str


graph=TopologicalMap()
graph.upsert_node(PlaceNode("living_room","Living room","room"))
graph.upsert_node(PlaceNode("hallway","East hallway","corridor",{"description":"blue sofa on left"}))
graph.add_edge(PlaceEdge("living_room","hallway",gateway_entity="door_04"))
graph.update_gateway("door_04","open",("door-frame",))

context=RichContextBuilder(ExampleState()).build(
    goal="Put away the Halloween decorations",
    focus_entities=("candle_2","cabinet_A"),
    image_evidence=["img-current-head"],
    runtime_events=[
        Event("skill_failed",63.0,{"skill_id":"pick-candle-2","reason":"possible bowl obstruction"},"evt-34"),
        Event("decision_required",70.0,{},"evt-35"),
    ],
    topology=graph,
    current_place="living_room",
    observation_coverage=[
        CoverageNote("coffee_table_surface",70.0,"high","seen",("img-current-head",),
                     "candle_2 visible; no need to search another room")
    ],
)
print(json.dumps(context,indent=2))
