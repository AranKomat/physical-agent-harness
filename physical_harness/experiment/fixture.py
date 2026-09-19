"""Deterministic pixel fixture. NOT BEHAVIOR, not robot competence, and not a model benchmark."""
from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

from ..contracts import SkillReceipt
from .actors import Goal
from .journal import Journal
from .models import JsonModel, ModelSettings, Rates
from .native import BeliefEstimate, CameraCapture, NativeBindings, ObjectBox, Observation
from .runner import Action, EpisodeRunner, RunLimits
from .validation import dumps, loads


class FixtureTransport:
    def __init__(self):
        self.calls = []

    def post(self, path, payload):
        self.calls.append((path, payload))
        if path == "/responses/input_tokens":
            return {"object": "response.input_tokens", "input_tokens": 100}
        blocks = payload["input"][0]["content"]
        context = loads(blocks[0]["text"])
        schema = payload["text"]["format"]["schema"]["properties"]
        if "tool" in schema:
            done = all(g["status"] == "observed_complete" for g in context["task_ledger"])
            answer = {"tool": "finish" if done else "run_skill", "arguments": {
                "action_id": None if done else "close-cabinet", "goal_id": None if done else "closed",
                "reason": "Deterministic fixture decision, not language-model reasoning"},
                "information_need": {
                    "prior_event": False,
                    "prior_place": False,
                    "failure_or_recovery_history": False,
                    "revisit_comparison": False,
                    "visual_identity_continuity": False,
                    "visual_motion_comparison": False,
                    "visual_appearance_comparison": False,
                    "historical_geometry": False,
                }}
        elif "verdict" in schema:
            images = [b for b in blocks if b["type"] == "input_image"]
            raw = base64.b64decode(images[-1]["image_url"].split(",", 1)[1])
            with Image.open(BytesIO(raw)) as image:
                green = image.getpixel((32, 24))[1] > 180
            answer = {"verdict": "verified" if green else "rejected", "confidence": .99,
                      "evidence_ids": [context["after"][-1]["id"]], "tier": 3,
                      "reason": "Fixture checks real attached image pixels; not a trained verifier"}
        else:
            answer = {"text": "Synthetic fixture image.",
                      "cited_asset_ids": list(context["card"]["asset_ids"])[:1]}
        return {"id": "fixture-response", "status": "completed", "service_tier": "default",
                "usage": {"input_tokens": 100, "output_tokens": 80,
                          "input_tokens_details": {"cached_tokens": 0}},
                "output": [{"type": "message", "role": "assistant",
                            "content": [{"type": "output_text", "text": dumps(answer).decode()}]}]}


class FixtureNative:
    def __init__(self, episode):
        self.episode, self.t, self.closed, self.stops = episode, 0.0, False, 0

    def observe(self):
        image = Image.new("RGB", (64, 48), (30, 30, 30))
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 8, 48, 40), fill=(10, 230, 10) if self.closed else (230, 10, 10))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return Observation(self.episode, f"obs-{self.t}", self.t,
                           (CameraCapture("head", buffer.getvalue()),),
                           (BeliefEstimate("cabinet", "open_state", "closed" if self.closed else "open",
                                           "head", "observed"),),
                           (ObjectBox("cabinet", "head", (16, 8, 49, 41), "fixture cabinet"),),
                           "fixture-room", "Synthetic pixels; not a real room")

    def run_skill(self, request):
        start = self.t
        self.t += 1
        self.closed = True
        return SkillReceipt(request.skill_id, "synthetic-native", "completed", start, self.t,
                            policy_calls=1, chunks_generated=1, action_steps_executed=1,
                            metadata={"episode_id": self.episode, "execution_epoch": request.execution_epoch,
                                      "stop_acknowledged": True})

    def stop(self):
        self.stops += 1
        return True

    def bindings(self):
        return NativeBindings("synthetic-fixture-NOT-BEHAVIOR", self.observe, self.run_skill,
                              self.stop, simulated=True, qualification_id="synthetic-contract-test-only")


def run_demo(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    journal = Journal(output / "journal.sqlite", "fixture-episode", max_microusd=0, max_calls=8)
    transport = FixtureTransport()
    settings = ModelSettings("fixture-model-not-a-real-model", paid=False)
    model = JsonModel(settings, transport, journal,
                      {"default": Rates("0", "0", "0", "deterministic fixture; no API calls")})
    native = FixtureNative("fixture-episode")
    runner = EpisodeRunner(
        output, "fixture-episode", "Close the synthetic cabinet", native.bindings(),
        [Goal("closed", "CLOSED(cabinet)", ("cabinet", "open_state", "closed"),
              "Fixture only: green center indicates closed; not a real-world visual criterion",
              ("cabinet",), verifier_qualification="synthetic-pixel-check-only")],
        [Action("close-cabinet", "close cabinet", ("cabinet",), "closed")],
        model, model, journal, limits=RunLimits(allow_motion=True))
    try:
        report = runner.run()
        report["http_requests"] = 0
        report["physical_robot_actions"] = 0
        report["synthetic_native_actions"] = native.t
        report["request_shapes_checked"] = len(transport.calls)
        (output / "demo-report.json").write_bytes(dumps(report))
        return report
    finally:
        runner.close()
        journal.close()


def rpc_fixture_factory(episode):
    """Only for checking the actual subprocess protocol without a simulator."""
    return FixtureNative(episode).bindings()
