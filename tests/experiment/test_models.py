from __future__ import annotations

import base64

import pytest

from physical_harness.experiment.fixture import FixtureTransport
from physical_harness.experiment.journal import BudgetExceeded, DuplicateCall, Journal
from physical_harness.experiment.media import ImageInput
from physical_harness.experiment.models import JsonModel, ModelSettings, Rates
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
