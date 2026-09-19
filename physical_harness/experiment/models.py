"""Real Responses/Chat adapters, explicit rates, actual image inputs, local validation."""
from __future__ import annotations

import time
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal
from typing import Any, Protocol

from .journal import Journal
from .media import ImageInput, validate_images
from .validation import digest, dumps, integer, loads, text, validate_schema


class Poster(Protocol):
    def post(self, path: str, payload: dict) -> dict: ...


@dataclass(frozen=True)
class Rates:
    # USD / million tokens numerically equals micro-USD / token.
    input: str
    cached_input: str
    output: str
    reference: str

    def __post_init__(self):
        for value in (self.input, self.cached_input, self.output):
            n = Decimal(value)
            if not n.is_finite() or n < 0:
                raise ValueError("Rates must be explicit finite nonnegative decimal strings")
        if Decimal(self.cached_input) > Decimal(self.input):
            raise ValueError("Cache rate exceeds uncached rate; reservation policy needs review")
        text(self.reference, "rate-card provenance")

    def cost(self, inputs: int, outputs: int, cached: int = 0) -> int:
        for value in (inputs, outputs, cached):
            integer(value)
        if cached > inputs:
            raise ValueError("Invalid cached token count")
        total = ((inputs - cached) * Decimal(self.input) + cached * Decimal(self.cached_input)
                 + outputs * Decimal(self.output))
        return int(total.to_integral_value(rounding=ROUND_CEILING))


@dataclass(frozen=True)
class ModelSettings:
    model: str
    dialect: str = "responses"
    service_tier: str | None = None
    reasoning_effort: str | None = None
    max_input_tokens: int = 32768
    max_output_tokens: int = 2048
    max_images: int = 14
    max_pixels: int = 12_000_000
    detail: str = "high"
    paid: bool = True
    allow_paid: bool = False
    # For Chat-compatible local servers there is no universal image-aware counter.
    # An approved model-specific counter must be injected for paid chat endpoints.
    use_input_token_endpoint: bool = True

    def __post_init__(self):
        text(self.model, "exact provider model ID", 256)
        if "REPLACE" in self.model or self.model.lower() in {"unspecified", "todo"}:
            raise ValueError("Configure an actual accessible model ID")
        if self.dialect not in {"responses", "chat"}:
            raise ValueError("Unsupported provider dialect")
        for n in (self.max_input_tokens, self.max_output_tokens, self.max_images, self.max_pixels):
            integer(n, minimum=1)
        if self.detail not in {"low", "high", "auto", "original"}:
            raise ValueError("Invalid image detail")
        for v in (self.paid, self.allow_paid, self.use_input_token_endpoint):
            if type(v) is not bool:
                raise ValueError("Provider permissions must be booleans")


class JsonModel:
    """Every call is independent; no previous_response_id or hidden conversation."""
    def __init__(self, settings: ModelSettings, transport: Poster, journal: Journal,
                 rates: dict[str, Rates], *, input_counter=None):
        self.settings, self.transport, self.journal = settings, transport, journal
        self.rates, self.input_counter = dict(rates), input_counter
        if not self.rates:
            raise ValueError("Explicit tier rates required, including for zero-API-price local runs")
        if settings.service_tier is not None and settings.service_tier not in rates:
            raise ValueError("Requested tier has no declared rates")
        self.name = settings.model

    def _payload(self, instruction: str, context: dict, images: list[ImageInput], schema: dict):
        s = self.settings
        blocks = [{"type": "input_text", "text": dumps(context).decode()}]
        for image in images:
            blocks += [{"type": "input_text", "text": "IMAGE " + dumps(image.metadata()).decode()},
                       {"type": "input_image", "image_url": image.data_url(), "detail": s.detail}]
        if s.dialect == "responses":
            body = {"model": s.model, "instructions": instruction,
                    "input": [{"role": "user", "content": blocks}],
                    "text": {"format": {"type": "json_schema", "name": "physical_agent",
                                        "strict": True, "schema": schema}},
                    "max_output_tokens": s.max_output_tokens, "store": False,
                    "truncation": "disabled"}
            if s.service_tier:
                body["service_tier"] = s.service_tier
            if s.reasoning_effort:
                body["reasoning"] = {"effort": s.reasoning_effort}
            return "/responses", body
        content = []
        for block in blocks:
            if block["type"] == "input_text":
                content.append({"type": "text", "text": block["text"]})
            else:
                content.append({"type": "image_url", "image_url": {
                    "url": block["image_url"], "detail": block["detail"]}})
        body = {"model": s.model, "messages": [
            {"role": "system", "content": instruction}, {"role": "user", "content": content}],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "physical_agent", "strict": True, "schema": schema}},
            "max_tokens": s.max_output_tokens, "stream": False}
        if s.reasoning_effort or s.service_tier:
            raise ValueError("Chat optional parameters must be qualified before use")
        return "/chat/completions", body

    def call(self, call_id: str, role: str, instruction: str, context: dict,
             images: list[ImageInput], schema: dict) -> dict[str, Any]:
        s = self.settings
        if s.paid and not s.allow_paid:
            raise PermissionError("Paid generation is not authorized")
        if context.get("episode") != self.journal.episode:
            raise ValueError("Model context belongs to another episode")
        validate_images(images, self.journal.episode, max_images=s.max_images, max_pixels=s.max_pixels)
        text(instruction, "system instruction", 32000)
        if len(dumps(context)) > 256_000:
            raise ValueError("Context metadata too large")
        path, body = self._payload(instruction, context, images, schema)
        manifest = {"model": s.model, "dialect": s.dialect, "instruction": instruction,
                    "context": context, "images": [i.metadata() for i in images],
                    "schema": schema, "service_tier": s.service_tier,
                    "reasoning_effort": s.reasoning_effort, "detail": s.detail,
                    "max_output_tokens": s.max_output_tokens,
                    "wire_sha256": digest(body),
                    "rates": {k: vars(v) for k, v in self.rates.items()}}
        upper = max(r.cost(s.max_input_tokens, s.max_output_tokens) for r in self.rates.values())
        # Reserve BEFORE preflight network work. Failure remains an unresolved upper bound.
        self.journal.reserve(call_id, role, manifest, upper)
        start = time.monotonic()
        try:
            if s.dialect == "responses" and s.use_input_token_endpoint:
                count_body = {k: body[k] for k in ("model", "input", "instructions", "text")}
                count_reply = self.transport.post("/responses/input_tokens", count_body)
                input_count = integer(count_reply["input_tokens"])
                count_method = "provider_input_tokens"
            elif self.input_counter is not None:
                input_count = integer(self.input_counter(body))
                count_method = "operator_qualified_counter"
            elif s.paid:
                raise ValueError("Paid models require image-aware input accounting")
            else:
                input_count, count_method = None, "unavailable_local_no_api_charge"
            if input_count is not None and input_count > s.max_input_tokens:
                raise ValueError("Input token count exceeds configured maximum")
            self.journal.put("preflight", call_id, {"input_tokens": input_count,
                                                   "method": count_method})
            raw = self.transport.post(path, body)
            usage = raw.get("usage")
            if not isinstance(usage, dict):
                raise ValueError("Provider omitted usage; spend cannot be reconciled")
            if s.dialect == "responses":
                inputs = integer(usage["input_tokens"])
                outputs = integer(usage["output_tokens"])
                cached = integer((usage.get("input_tokens_details") or {}).get("cached_tokens", 0))
                completed = raw.get("status") == "completed"
                chunks = [item for output in raw.get("output", [])
                          if output.get("type") == "message" and output.get("role") == "assistant"
                          for item in output.get("content", [])]
                if any(c.get("type") == "refusal" for c in chunks):
                    content = None
                else:
                    texts = [c["text"] for c in chunks if c.get("type") == "output_text"]
                    content = texts[0] if len(texts) == 1 else None
            else:
                inputs, outputs = integer(usage["prompt_tokens"]), integer(usage["completion_tokens"])
                cached = integer((usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0))
                choices = raw.get("choices", [])
                completed = len(choices) == 1 and choices[0].get("finish_reason") == "stop"
                content = choices[0].get("message", {}).get("content") if len(choices) == 1 else None
            returned_tier = raw.get("service_tier")
            if s.paid and s.dialect == "responses" and returned_tier is None:
                raise ValueError("Provider omitted actual service tier; charge remains reserved")
            tier = returned_tier or s.service_tier or "default"
            if tier not in self.rates:
                raise ValueError("Actual provider tier lacks a declared rate card")
            actual = self.rates[tier].cost(inputs, outputs, cached)
            report = {"response_id": raw.get("id"), "usage": usage, "actual_tier": tier,
                      "seconds": time.monotonic() - start, "status": raw.get("status"),
                      "completed": completed, "output_text": content}
            self.journal.complete(call_id, report, actual)
            if inputs > s.max_input_tokens or outputs > s.max_output_tokens:
                raise ValueError("Usage exceeded declared model token bounds")
            if not completed or not isinstance(content, str):
                raise ValueError("Incomplete/refused/unsupported model response; no action")
            result = loads(content)
            validate_schema(result, schema)
            return result
        except Exception as exc:
            self.journal.fail(call_id, type(exc).__name__)
            raise
