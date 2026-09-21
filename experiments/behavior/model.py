"""Standalone bounded OpenRouter transport, retaining the frozen Flex wire recipe.

No private campaign imports, retries, fallback, implicit credentials, or paid
calls on import. Existing Journal/HttpTransport own durable holds and deadlines.
"""

import json
import math
import time
import urllib.request
from decimal import Decimal

from physical_harness.experiment.journal import BudgetExceeded, Journal
from physical_harness.experiment.media import validate_images
from physical_harness.experiment.transport import HttpTransport
from physical_harness.experiment.validation import validate_schema

INPUT_BOUND = 24_000
OUTPUT_BOUND = 512
CALL_CAP = 159_360


def qualify_endpoint(data, config):
    if "image" not in data["architecture"]["input_modalities"]:
        raise ValueError("Visual endpoint required")
    endpoint = next(e for e in data["endpoints"] if e["tag"] == config.provider)
    if endpoint.get("status") != 0 or endpoint.get("context_length", 0) < INPUT_BOUND:
        raise ValueError("Selected route unavailable or context too small")
    prices = {k: Decimal(str(v)) for k, v in endpoint["pricing"].items()}
    allowed = {"prompt", "completion", "input_cache_read", "input_cache_write", "discount"}
    if any(not v.is_finite() or v < 0 or (k not in allowed and v != 0)
           for k, v in prices.items()):
        raise ValueError("Unbudgeted or invalid endpoint pricing")
    if (prices["prompt"] != Decimal(config.expected_prompt_usd_per_token)
            or prices["completion"] != Decimal(config.expected_completion_usd_per_token)):
        raise ValueError("Pricing changed; review the protocol before paid dispatch")
    if not isinstance(endpoint.get("provider_name"), str) or not endpoint["provider_name"]:
        raise ValueError("Provider identity is missing")
    return endpoint


def endpoint_preflight(config, *, allow_network=False):
    if not allow_network:
        raise PermissionError("Network opt-in required")
    # Fixed public metadata URL; credentials are never sent in this request.
    url = f"https://openrouter.ai/api/v1/models/{config.model}/endpoints"
    with urllib.request.urlopen(url, timeout=30) as response:
        content = response.read(1_000_001)
    if len(content) > 1_000_000:
        raise ValueError("Endpoint metadata too large")
    data = json.loads(content)["data"]
    return qualify_endpoint(data, config)


def require_headroom(journal, calls, microusd):
    roles = journal.report()["roles"]
    if any(r["unresolved"] for r in roles):
        raise BudgetExceeded("Unknown prior spend: reconcile before another run")
    if (sum(r["calls"] for r in roles) + calls > journal.max_calls
            or sum(r["exposure"] for r in roles) + microusd > journal.max_microusd):
        raise BudgetExceeded("Insufficient cumulative headroom for the frozen pair")


def open_campaign(config):
    config.journal.parent.mkdir(parents=True, exist_ok=True)
    return Journal(config.journal, "behavior-matched-campaign-v1",
                   max_calls=config.max_calls, max_microusd=config.max_microusd)


def request_body(config, endpoint, instruction, context, images, schema):
    content = [{"type": "text", "text": json.dumps(context, separators=(",", ":"))}]
    # Historical recipe: byte-level text allowance, 3100/image, 4096 wrapper
    # allowance. The schema is now counted too. Not a generic tokenizer.
    bound = 4096 + len(instruction.encode()) + len(json.dumps(schema).encode())
    bound += len(content[0]["text"].encode())
    for image in images:
        label = "IMAGE " + json.dumps(image.metadata())
        bound += len(label.encode()) + 3100
        content.extend([{"type": "text", "text": label},
                        {"type": "image_url", "image_url": {
                            "url": image.data_url(), "detail": "high"}}])
    if bound > INPUT_BOUND:
        raise ValueError("Packet exceeds approved image-aware input allowance")
    prices = endpoint["pricing"]
    inp = max(Decimal(prices["prompt"]), Decimal(prices.get("input_cache_write", "0")))
    out = Decimal(prices["completion"])
    upper = math.ceil(Decimal("1.2") * (inp * bound + out * OUTPUT_BOUND) * 1_000_000)
    if not 0 <= upper <= CALL_CAP:
        raise BudgetExceeded("Packet exceeds the frozen per-call reservation")
    return {
        "model": config.model,
        "messages": [{"role": "system", "content": instruction},
                     {"role": "user", "content": content}],
        "service_tier": "flex", "reasoning": {"effort": "medium"},
        "max_tokens": OUTPUT_BOUND, "stream": False,
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "physical_agent", "strict": True, "schema": schema}},
        "provider": {"only": [config.provider], "allow_fallbacks": False,
                     "require_parameters": True, "max_price": {
                         "prompt": float(inp * 1_200_000),
                         "completion": float(out * 1_200_000)}},
    }, bound, upper


class RadioModel:
    def __init__(self, config, endpoint, local, campaign, *, allow_network=False,
                 allow_paid=False, transport=None):
        if not allow_paid or not allow_network:
            raise PermissionError("Explicit paid and network opt-ins required")
        self.config, self.endpoint = config, endpoint
        self.local, self.campaign = local, campaign
        self.transport = transport or HttpTransport(
            "https://openrouter.ai/api/v1", config.api_key_env,
            allow_network=True, timeout_s=300)

    def call(self, call_id, role, instruction, context, images, schema):
        if context.get("episode") != self.local.episode:
            raise ValueError("Foreign model context")
        validate_images(images, self.local.episode, max_images=3, max_pixels=3_000_000)
        body, bound, upper = request_body(
            self.config, self.endpoint, instruction, context, images, schema)
        manifest = {"model": self.config.model, "provider": self.config.provider,
                    "instruction": instruction, "context": context, "schema": schema,
                    "input_token_bound": bound, "output_token_bound": OUTPUT_BOUND,
                    "images": [im.metadata() for im in images]}
        self.campaign.reserve(call_id, role, manifest, upper)
        try:
            self.local.reserve(call_id, role, manifest, upper)
            start = time.monotonic()
            raw = self.transport.post("/chat/completions", body)
            providers = self.endpoint.get("routing_provider_names",
                                          [self.endpoint["provider_name"]])
            models = self.endpoint.get("routing_response_models", [self.config.model])
            if (raw.get("provider") not in providers or raw.get("model") not in models
                    or raw.get("service_tier") != "flex"):
                raise ValueError("Unverified provider/model/tier; no fallback")
            usage = raw["usage"]
            cost = Decimal(str(usage["cost"]))
            if not cost.is_finite() or cost < 0:
                raise ValueError("Missing or invalid billed cost")
            actual = math.ceil(cost * 1_000_000)
            report = {"raw": raw, "seconds": time.monotonic() - start}
            # Settle known charges even when schema/termination validation fails.
            try:
                self.campaign.complete(call_id, report, actual)
            finally:
                self.local.complete(call_id, report, actual)
            for name, limit in (("prompt_tokens", bound), ("completion_tokens", OUTPUT_BOUND)):
                if type(usage.get(name)) is not int or not 0 <= usage[name] <= limit:
                    raise ValueError("Provider exceeded declared token allowance")
            choices = raw.get("choices", [])
            if len(choices) != 1 or choices[0].get("finish_reason") != "stop":
                raise ValueError("Incomplete model response")
            message = choices[0]["message"]
            if (message.get("role") != "assistant" or message.get("tool_calls")
                    or message.get("refusal")):
                raise ValueError("Unexpected tool/refusal response")
            value = json.loads(message["content"])
            validate_schema(value, schema)
            return value
        except BaseException as error:
            self.campaign.fail(call_id, type(error).__name__)
            self.local.fail(call_id, type(error).__name__)
            raise
