"""Synthetic wiring example for MemorySidecar.

No model calls, robot actions, or benchmark state. Replace only the observation
source, evidence resolver, and runtime events in a real shadow-mode integration.
"""
from __future__ import annotations

import argparse
import json
from io import BytesIO
from pathlib import Path

from PIL import Image

from physical_harness.core.events import EventBus, EventType, RuntimeEvent
from physical_harness.core.evidence import EvidenceStore
from physical_harness.integrations.sensors.behavior import BehaviorAdapter
from physical_harness.world.memory.integration import DecisionCutoffLog, MemorySidecar
from physical_harness.world.memory.store import MemoryStore


def png(width, height, rgb):
    image = Image.new("RGB", (width, height), rgb)
    out = BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=False)

    blobs = EvidenceStore(root / "evidence")
    first = blobs.put(png(64, 48, (180, 20, 20)), ".png")
    second = blobs.put(png(64, 48, (20, 20, 180)), ".png")

    def env(obs, t, ref):
        return {
            "schema_version": 1, "episode_id": "demo", "observation_id": obs,
            "sim_time": t, "rgb_refs": {"head": ref},
            "depth_refs": {"head": "not-used-by-memory"},
            "proprioception": {"joint_positions": [0.0]},
            "camera_intrinsics": {"head": {
                "width": 64, "height": 48, "fx": 50, "fy": 50,
                "cx": 32, "cy": 24, "depth_scale_m": 0.001}},
            "camera_frames": {"head": "head_optical"},
        }

    with MemoryStore(root / "episodic.sqlite", "demo", blobs.read) as memory:
        decisions = DecisionCutoffLog(root / "decisions.sqlite", "demo")
        sidecar = MemorySidecar(
            episode_id="demo", store=memory, decisions=decisions,
            resolve_rgb_ref=lambda ref: ref,
        )

        class Source:
            def __init__(self):
                self.actions = []

            def reset(self):
                return env("o1", 1.0, first)

            def step(self, action):
                self.actions.append(action)
                return env("o2", 2.0, second)

        source = Source()
        behavior = BehaviorAdapter(
            source,
            episode_id="demo",
            action_bounds=[[-1, 1]],
            logger=sidecar.ingest_observation,
        )
        events = EventBus()
        events.subscribe(sidecar.record_event)

        behavior.reset()
        sidecar.bind_skill("pick-1", entity_ids=("red_object",), place_ids=("table",))
        events.publish(
            RuntimeEvent(
                EventType.SKILL_FAILED,
                "demo",
                1.0,
                {"skill_id": "pick-1"},
                event_id="event-1",
            )
        )
        behavior.step([0.0], source_observation_id="o1")
        events.publish(
            RuntimeEvent(
                EventType.DECISION_REQUIRED,
                "demo",
                2.0,
                event_id="event-2",
            )
        )
        base = {"episode": "demo", "goal": "find the red object", "images": []}
        unchanged, decision, packet = sidecar.prepare_decision(
            decision_id="decision-1", event_id="event-2", observed_through=2.0,
            base_context=base, entity_id="red_object", active=False,
        )
        report = {
            "mode": "shadow",
            "base_unchanged": unchanged == base,
            "adapter_actions": len(source.actions),
            "cutoff": decision.cutoff.__dict__,
            "retrieved_cards": [card["card_id"] for card in packet["cards"]],
            "historical_images": [image["asset_id"] for image in packet["images"]],
        }
        (root / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        decisions.close()
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
