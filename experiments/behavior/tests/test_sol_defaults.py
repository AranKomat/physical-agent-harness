from pathlib import Path

import pytest

from experiments.behavior.config import ModelConfig, load_config
from experiments.behavior.model import qualify_endpoint, request_body


def test_active_example_defaults_and_caps():
    root = Path(__file__).resolve().parents[3]
    config = load_config(root / "configs/behavior/matched-radio.example.json")
    assert config.model == ModelConfig()
    assert config.model.model == "openai/gpt-6-sol"
    assert config.model.provider == "openai/flex"
    assert config.campaign.max_calls == 36
    assert config.campaign.max_microusd == 6_000_000


def test_sol_flex_request_with_mock_endpoint_only():
    cfg = ModelConfig()
    endpoint = {"tag": "openai/flex", "status": 0, "context_length": 100_000,
                "provider_name": "OpenAI", "pricing": {"prompt": "0.000001",
                "completion": "0.000005", "input_cache_write": "0.00000125"}}
    qualified = qualify_endpoint({"architecture": {"input_modalities": ["image"]},
                                  "endpoints": [endpoint]}, cfg)
    body, _, _ = request_body(cfg, qualified, "JSON", {}, [], {"type": "object"})
    assert body["model"] == "openai/gpt-6-sol"
    assert body["service_tier"] == "flex"
    assert body["reasoning"] == {"effort": "medium"}
    assert body["provider"]["allow_fallbacks"] is False
    endpoint["pricing"]["prompt"] = "0.000002"
    with pytest.raises(ValueError, match="Pricing changed"):
        qualify_endpoint({"architecture": {"input_modalities": ["image"]}, "endpoints": [endpoint]}, cfg)


def test_historical_astra_is_explicit_and_prices_cannot_cross_cohorts():
    cfg = ModelConfig(model="openai/gpt-6-astra")
    assert (cfg.expected_prompt_usd_per_token, cfg.expected_completion_usd_per_token) == (
        "0.000005", "0.000025")
    with pytest.raises(ValueError, match="cohort"):
        ModelConfig(expected_prompt_usd_per_token="0.000005")
    with pytest.raises(ValueError, match="cohort"):
        ModelConfig(model="openai/gpt-6-astra", expected_completion_usd_per_token="0.000005")


def test_retired_luna_is_not_an_active_model_option():
    with pytest.raises(ValueError):
        ModelConfig(model="openai/gpt-6-luna")


@pytest.mark.parametrize("model,prompt,completion", [
    ("openai/gpt-6-luna", "0.000001", "0.000005"),
    ("openai/gpt-6-sol", "0.00000005", "0.00000025"),
    ("openai/gpt-6-astra", "0.00000005", "0.00000025"),
])
def test_luna_prices_cannot_cross_cohorts(model, prompt, completion):
    with pytest.raises(ValueError):
        ModelConfig(model=model, expected_prompt_usd_per_token=prompt,
                    expected_completion_usd_per_token=completion)
