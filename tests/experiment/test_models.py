from __future__ import annotations

import base64
from pathlib import Path

import pytest

from physical_harness.experiment.fixture import FixtureTransport
from physical_harness.experiment.journal import BudgetExceeded, DuplicateCall, Journal
from physical_harness.experiment.media import ImageInput
from physical_harness.experiment.models import (
    CodexExecJsonModel,
    CodexExecSettings,
    JsonModel,
    ModelSettings,
    Rates,
)
from physical_harness.experiment.validation import loads

SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}},
          "required": ["answer"], "additionalProperties": False}


class AnswerTransport(FixtureTransport):
    def post(self, path, payload):
        self.calls.append((path, payload))
        if path.endswith("input_tokens"):
            return {"input_tokens": 20}
        return {"id": "test", "status": "completed", "service_tier": "default",
                "usage": {"input_tokens": 20, "output_tokens": 5,
                          "input_tokens_details": {"cached_tokens": 10}},
                "output": [{"type": "message", "role": "assistant", "content": [
                    {"type": "output_text", "text": '{"answer":"ok"}'}]}]}


def client(tmp_path, *, paid=False, allow_paid=False, budget=100000, transport=None):
    journal = Journal(tmp_path / "journal.sqlite", "ep", max_microusd=budget, max_calls=4)
    settings = ModelSettings("test-model", paid=paid, allow_paid=allow_paid,
                             max_input_tokens=100, max_output_tokens=10)
    transport = transport or AnswerTransport()
    model = JsonModel(settings, transport, journal, {"default": Rates("1", ".5", "2", "test rate")})
    return model, transport, journal


def test_responses_image_payload_contains_pixels_and_usage(tmp_path):
    import hashlib

    from physical_harness.experiment.fixture import FixtureNative
    data = FixtureNative("ep").observe().cameras[0].data
    image = ImageInput("frame", "ep", hashlib.sha256(data).hexdigest() + ".png",
                       0, "head", 64, 48, data)
    model, transport, journal = client(tmp_path)
    assert model.call("call", "verifier", "Judge", {"episode": "ep"}, [image], SCHEMA) == {"answer": "ok"}
    body = transport.calls[-1][1]
    blocks = body["input"][0]["content"]
    encoded_image = next(b["image_url"] for b in blocks if b["type"] == "input_image")
    assert base64.b64decode(encoded_image.split(",", 1)[1]) == data
    assert body["store"] is False and body["truncation"] == "disabled"
    assert body["text"]["format"]["schema"] == SCHEMA
    assert journal.report()["roles"][0]["accounted"] == 25
    saved = journal.db.execute("SELECT request FROM calls").fetchone()[0]
    assert "data:image" not in saved and "Bearer" not in saved
    journal.close()


def test_paid_requires_explicit_opt_in(tmp_path):
    model, transport, journal = client(tmp_path, paid=True)
    with pytest.raises(PermissionError):
        model.call("call", "executive", "Judge", {"episode": "ep"}, [], SCHEMA)
    assert transport.calls == []
    journal.close()


def test_budget_rejects_before_network_and_duplicate_never_retries(tmp_path):
    model, transport, journal = client(tmp_path, budget=0)
    with pytest.raises(BudgetExceeded):
        model.call("c1", "executive", "Judge", {"episode": "ep"}, [], SCHEMA)
    assert transport.calls == []
    journal.close()
    other = tmp_path / "other"
    other.mkdir()
    model, transport, journal = client(other)
    model.call("c1", "executive", "Judge", {"episode": "ep"}, [], SCHEMA)
    count = len(transport.calls)
    with pytest.raises(DuplicateCall):
        model.call("c1", "executive", "Judge", {"episode": "ep"}, [], SCHEMA)
    assert len(transport.calls) == count
    journal.close()


def test_timeout_retains_reservation(tmp_path):
    class Broken:
        def post(self, path, payload):
            raise TimeoutError("server outcome unknown")
    model, _, journal = client(tmp_path, transport=Broken())
    with pytest.raises(TimeoutError):
        model.call("c1", "executive", "Judge", {"episode": "ep"}, [], SCHEMA)
    row = journal.report()["roles"][0]
    assert row["unresolved"] == 1 and row["exposure"] == 120
    journal.close()


@pytest.mark.parametrize("mutation", ["incomplete", "refusal", "invalid_json", "wrong_schema", "unknown_tier"])
def test_invalid_provider_result_never_yields_action(tmp_path, mutation):
    class Bad(AnswerTransport):
        def post(self, path, payload):
            result = super().post(path, payload)
            if path.endswith("input_tokens"):
                return result
            if mutation == "incomplete":
                result["status"] = "incomplete"
            elif mutation == "refusal":
                result["output"][0]["content"] = [{"type": "refusal", "refusal": "no"}]
            elif mutation == "invalid_json":
                result["output"][0]["content"][0]["text"] = "not JSON"
            elif mutation == "wrong_schema":
                result["output"][0]["content"][0]["text"] = '{"tool":"torque"}'
            else:
                result["service_tier"] = "unpriced-tier"
            return result
    model, _, journal = client(tmp_path, transport=Bad())
    with pytest.raises(Exception):
        model.call("c1", "executive", "Judge", {"episode": "ep"}, [], SCHEMA)
    assert journal.report()["roles"][0]["calls"] == 1
    journal.close()


def test_input_count_stops_generation(tmp_path):
    class TooLarge(AnswerTransport):
        def post(self, path, payload):
            self.calls.append((path, payload))
            return {"input_tokens": 101}
    model, transport, journal = client(tmp_path, transport=TooLarge())
    with pytest.raises(ValueError):
        model.call("c1", "executive", "Judge", {"episode": "ep"}, [], SCHEMA)
    assert [p for p, _ in transport.calls] == ["/responses/input_tokens"]
    journal.close()


def test_chat_shapes_and_local_usage(tmp_path):
    class Chat:
        calls = []
        def post(self, path, payload):
            self.calls.append((path, payload))
            return {"id": "chat", "choices": [{"finish_reason": "stop", "message": {
                "content": '{"answer":"ok"}'}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 4}}
    journal = Journal(tmp_path / "j.sqlite", "ep", max_microusd=0, max_calls=2)
    transport = Chat()
    model = JsonModel(ModelSettings("local-qwen-test", dialect="chat", paid=False,
                                    use_input_token_endpoint=False), transport, journal,
                      {"default": Rates("0", "0", "0", "local: API tariff zero; GPU excluded")})
    assert model.call("c", "narrator", "Judge", {"episode": "ep"}, [], SCHEMA)["answer"] == "ok"
    assert transport.calls[-1][0] == "/chat/completions"
    assert transport.calls[-1][1]["response_format"]["json_schema"]["strict"] is True
    journal.close()


def test_duplicate_json_fields_rejected():
    with pytest.raises(ValueError):
        loads('{"answer":"ok","answer":"not ok"}')
    with pytest.raises(ValueError):
        loads('{"confidence":NaN}')


def test_journal_reopen_does_not_forget_unknown_charge(tmp_path):
    path = tmp_path / "j.sqlite"
    journal = Journal(path, "ep", max_microusd=100, max_calls=2)
    journal.reserve("c", "executive", {"x": 1}, 100)
    journal.fail("c", "TimeoutError")
    journal.close()
    journal = Journal(path, "ep", max_microusd=100, max_calls=2)
    with pytest.raises(BudgetExceeded):
        journal.reserve("d", "executive", {}, 1)
    journal.close()


def test_paid_missing_actual_tier_leaves_spend_unresolved(tmp_path):
    class MissingTier(AnswerTransport):
        def post(self, path, payload):
            result = super().post(path, payload)
            result.pop('service_tier', None)
            return result
    model, _, journal = client(tmp_path, paid=True, allow_paid=True, transport=MissingTier())
    try:
        with pytest.raises(ValueError, match='actual service tier'):
            model.call('c', 'executive', 'Judge', {'episode': 'ep'}, [], SCHEMA)
        assert journal.report()['roles'][0]['unresolved'] == 1
    finally:
        journal.close()


class FakeCodex:
    def __init__(self, *, auth="Logged in using ChatGPT", returncode=0, output='{"answer":"ok"}'):
        self.auth = auth
        self.returncode = returncode
        self.output = output
        self.calls = []

    def __call__(self, args, **kwargs):
        import subprocess
        from pathlib import Path

        self.calls.append((args, kwargs))
        if args[1:] == ["login", "status"]:
            return subprocess.CompletedProcess(args, 0, self.auth, "")
        output = args[args.index("--output-last-message") + 1]
        Path(output).write_text(self.output)
        events = (
            '{"type":"turn.completed","usage":{"input_tokens":40,'
            '"cached_input_tokens":10,"output_tokens":5}}\n'
        )
        return subprocess.CompletedProcess(args, self.returncode, events, "secret")


def codex_client(tmp_path, runner):
    journal = Journal(tmp_path / "codex.sqlite", "ep", max_microusd=0, max_calls=3)
    model = CodexExecJsonModel(
        CodexExecSettings("gpt-6-astra", reasoning_effort="medium"),
        journal,
        runner=runner,
    )
    return model, journal


def test_codex_exec_is_ephemeral_read_only_structured_and_subscription_accounted(tmp_path):
    import hashlib

    from physical_harness.experiment.fixture import FixtureNative

    data = FixtureNative("ep").observe().cameras[0].data
    image = ImageInput(
        "frame",
        "ep",
        hashlib.sha256(data).hexdigest() + ".png",
        0,
        "head",
        64,
        48,
        data,
    )
    fake = FakeCodex()
    model, journal = codex_client(tmp_path, fake)
    try:
        assert model.call("c", "verifier", "Judge", {"episode": "ep"}, [image], SCHEMA) == {
            "answer": "ok"
        }
        args, kwargs = fake.calls[-1]
        assert "--ephemeral" in args and args[args.index("--sandbox") + 1] == "read-only"
        assert "--ignore-user-config" in args and "--ignore-rules" in args
        assert Path(args[args.index("--cd") + 1]).name.startswith("physical-harness-codex-")
        assert args[args.index("--model") + 1] == "gpt-6-astra"
        assert kwargs["env"].get("OPENAI_API_KEY") is None
        assert kwargs["env"].get("CODEX_API_KEY") is None
        assert '"episode":"ep"' in kwargs["input"]
        saved = journal.db.execute("SELECT request,response FROM calls").fetchone()
        assert "chatgpt_subscription" in saved[0] and "data:image" not in saved[0]
        assert loads(saved[1])["usage"]["input_tokens"] == 40
        assert journal.report()["roles"][0]["accounted"] == 0
    finally:
        journal.close()


def test_codex_exec_rejects_non_chatgpt_auth_before_reservation(tmp_path):
    fake = FakeCodex(auth="Logged in using an API key")
    model, journal = codex_client(tmp_path, fake)
    try:
        with pytest.raises(PermissionError, match="signed in with ChatGPT"):
            model.call("c", "executive", "Judge", {"episode": "ep"}, [], SCHEMA)
        assert journal.report()["roles"] == []
    finally:
        journal.close()


@pytest.mark.parametrize(
    ("runner", "error"),
    [
        (FakeCodex(returncode=2), RuntimeError),
        (FakeCodex(output="not json"), ValueError),
    ],
)
def test_codex_exec_failure_is_ambiguous_and_never_retried(tmp_path, runner, error):
    model, journal = codex_client(tmp_path, runner)
    try:
        with pytest.raises(error):
            model.call("c", "executive", "Judge", {"episode": "ep"}, [], SCHEMA)
        row = journal.report()["roles"][0]
        assert row["calls"] == 1 and row["unresolved"] == 1
        assert len(runner.calls) == 2
    finally:
        journal.close()


def test_codex_exec_timeout_is_ambiguous_and_never_retried(tmp_path):
    import subprocess

    class TimeoutCodex(FakeCodex):
        def __call__(self, args, **kwargs):
            if args[1:] == ["login", "status"]:
                return super().__call__(args, **kwargs)
            self.calls.append((args, kwargs))
            raise subprocess.TimeoutExpired(args, kwargs["timeout"])

    runner = TimeoutCodex()
    model, journal = codex_client(tmp_path, runner)
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            model.call("c", "executive", "Judge", {"episode": "ep"}, [], SCHEMA)
        row = journal.report()["roles"][0]
        assert row["calls"] == 1 and row["unresolved"] == 1
        assert len(runner.calls) == 2
    finally:
        journal.close()
