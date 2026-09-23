import json

import pytest

from experiments.behavior.config import ModelConfig
from experiments.behavior.model import RadioModel, qualify_endpoint, require_headroom
from physical_harness.integrations.experiment.journal import BudgetExceeded, Journal
from physical_harness.integrations.experiment.transport import TransportFailure


def endpoint():
    return {"tag": "openai/flex", "status": 0, "context_length": 100_000,
            "provider_name": "OpenAI", "pricing": {"prompt": "0.000005",
            "completion": "0.000025", "input_cache_write": "0.00000625"}}


SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}},
          "required": ["ok"], "additionalProperties": False}


class Transport:
    def __init__(self):
        self.calls = []
        self.reply = {"provider": "OpenAI", "model": "openai/gpt-6-astra",
                      "service_tier": "flex", "usage": {"cost": "0.02",
                          "prompt_tokens": 100, "completion_tokens": 10},
                      "choices": [{"finish_reason": "stop", "message": {
                          "role": "assistant", "content": '{"ok": true}'}}]}
        self.error = False

    def post(self, path, body):
        self.calls.append((path, body))
        if self.error:
            raise TransportFailure("unknown delivery")
        return self.reply


@pytest.fixture
def setup(tmp_path):
    local = Journal(tmp_path / "local.sqlite", "test", max_calls=18, max_microusd=3_000_000)
    campaign = Journal(tmp_path / "campaign.sqlite", "campaign",
                       max_calls=36, max_microusd=6_000_000)
    transport = Transport()
    model = RadioModel(ModelConfig(model="openai/gpt-6-astra"), endpoint(), local, campaign,
                       allow_paid=True, allow_network=True, transport=transport)
    yield model, transport, local, campaign
    local.close()
    campaign.close()


def call(model, ident="test:executive:0"):
    return model.call(ident, "executive", "Return JSON", {"episode": "test"}, [], SCHEMA)


def test_role_request_and_two_budget_settlements(setup):
    model, transport, local, campaign = setup
    assert call(model) == {"ok": True}
    body = transport.calls[0][1]
    assert body["provider"]["allow_fallbacks"] is False
    assert body["provider"]["only"] == ["openai/flex"]
    assert body["service_tier"] == "flex" and body["max_tokens"] == 512
    assert body["reasoning"] == {"effort": "medium"}
    for journal in (local, campaign):
        assert journal.report()["roles"][0]["accounted"] == 20_000
        assert journal.report()["roles"][0]["unresolved"] == 0


def test_unknown_delivery_keeps_both_holds_and_never_retries(setup):
    model, transport, local, campaign = setup
    transport.error = True
    with pytest.raises(TransportFailure):
        call(model)
    for journal in (local, campaign):
        assert journal.report()["roles"][0]["unresolved"] == 1
    with pytest.raises(BudgetExceeded, match="Unknown"):
        require_headroom(campaign, 1, 1)
    assert len(transport.calls) == 1


@pytest.mark.parametrize("field,value", [("provider", "other"), ("model", "other"),
                                         ("service_tier", "default")])
def test_identity_mismatch_cannot_drive_robot(setup, field, value):
    model, transport, _, campaign = setup
    transport.reply[field] = value
    with pytest.raises(ValueError, match="Unverified"):
        call(model)
    assert campaign.report()["roles"][0]["unresolved"] == 1


@pytest.mark.parametrize("field,value", [("cost", "NaN"), ("cost", "-1")])
def test_invalid_cost_stays_reserved(setup, field, value):
    model, transport, _, campaign = setup
    transport.reply["usage"][field] = value
    with pytest.raises(ValueError):
        call(model)
    assert campaign.report()["roles"][0]["unresolved"] == 1


def test_actual_cost_overrun_stops_but_is_accounted(setup):
    model, transport, local, campaign = setup
    transport.reply["usage"]["cost"] = "10"
    with pytest.raises(BudgetExceeded):
        call(model)
    for journal in (local, campaign):
        assert journal.report()["roles"][0]["accounted"] == 10_000_000
    with pytest.raises(BudgetExceeded):
        require_headroom(campaign, 1, 1)


def test_malformed_output_settles_known_cost_without_action(setup):
    model, transport, _, campaign = setup
    transport.reply["choices"][0]["message"]["content"] = "not json"
    with pytest.raises(json.JSONDecodeError):
        call(model)
    assert campaign.report()["roles"][0]["accounted"] == 20_000


def test_large_packet_rejected_before_any_reservation(setup):
    model, transport, local, campaign = setup
    with pytest.raises(ValueError):
        model.call("large", "executive", "x" * 25_000, {"episode": "test"}, [], SCHEMA)
    assert not transport.calls and not local.report()["roles"] and not campaign.report()["roles"]


def test_duplicate_call_cannot_retry_paid_dispatch(setup):
    model, transport, _, _ = setup
    call(model)
    with pytest.raises(RuntimeError):
        call(model)
    assert len(transport.calls) == 1


def test_approval_flags_required(setup):
    _, transport, local, campaign = setup
    with pytest.raises(PermissionError):
        RadioModel(ModelConfig(model="openai/gpt-6-astra"), endpoint(), local, campaign, transport=transport)


@pytest.mark.parametrize("price", ["0.000006", "NaN", "-1"])
def test_endpoint_price_change_fails_closed(price):
    e = endpoint()
    e["pricing"]["prompt"] = price
    with pytest.raises(ValueError):
        qualify_endpoint({"architecture": {"input_modalities": ["image"]},
                          "endpoints": [e]}, ModelConfig(model="openai/gpt-6-astra"))


def test_new_pricing_dimension_rejected():
    e = endpoint()
    e["pricing"]["request"] = "1"
    with pytest.raises(ValueError):
        qualify_endpoint({"architecture": {"input_modalities": ["image"]},
                          "endpoints": [e]}, ModelConfig(model="openai/gpt-6-astra"))
