"""Real Responses/Chat adapters, explicit rates, actual image inputs, local validation."""
from __future__ import annotations

import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from typing import Any, Protocol

from .journal import Journal
from .media import ImageInput, validate_images
from .validation import digest, dumps, integer, loads, text, validate_schema


class Poster(Protocol):
    def post(self, path: str, payload: dict) -> dict: ...


class CommandRunner(Protocol):
    def __call__(self, args: list[str], **kwargs) -> subprocess.CompletedProcess[str]: ...


_MINIMAL_CODEX_DISABLED_FEATURES = (
    "apps",
    "browser_use",
    "browser_use_external",
    "browser_use_full_cdp_access",
    "code_mode_host",
    "computer_use",
    "goals",
    "hooks",
    "image_generation",
    "in_app_browser",
    "in_app_chat",
    "in_app_dictation",
    "in_app_local_automation",
    "multi_agent",
    "plugin_sharing",
    "plugins",
    "remote_plugin",
    "shell_snapshot",
    "shell_tool",
    "skill_mcp_dependency_install",
    "skill_search",
    "sleep_tool",
    "steer",
    "tool_call_mcp_elicitation",
    "unified_exec",
    "unified_exec_tty",
    "unavailable_dummy_tools",
    "view_image",
    "workspace_dependencies",
)


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


@dataclass(frozen=True)
class CodexExecSettings:
    """Experimental ChatGPT-authenticated Codex transport settings."""

    model: str
    reasoning_effort: str | None = None
    timeout_s: int = 300
    max_output_bytes: int = 1_000_000
    max_images: int = 14
    max_pixels: int = 12_000_000
    codex_binary: str = "codex"
    require_chatgpt_auth: bool = True
    minimal_agent_context: bool = True

    def __post_init__(self):
        text(self.model, "exact Codex model ID", 256)
        if "REPLACE" in self.model or self.model.lower() in {"unspecified", "todo"}:
            raise ValueError("Configure an actual accessible Codex model ID")
        text(self.codex_binary, "Codex executable", 1024)
        if self.reasoning_effort not in {
            None,
            "none",
            "minimal",
            "low",
            "medium",
            "high",
            "xhigh",
            "max",
            "ultra",
        }:
            raise ValueError("Unsupported Codex reasoning effort")
        for value in (self.timeout_s, self.max_output_bytes, self.max_images, self.max_pixels):
            integer(value, minimum=1)
        for value in (self.require_chatgpt_auth, self.minimal_agent_context):
            if type(value) is not bool:
                raise ValueError("Codex execution switches must be boolean")


class CodexExecJsonModel:
    """Stateless, schema-validated experimental calls through ``codex exec``.

    This consumes the signed-in user's Codex allowance. It records zero API
    dollars while preserving call counts, token usage, timing, and failures.
    """

    def __init__(self, settings: CodexExecSettings, journal: Journal, *, runner=None):
        self.settings = settings
        self.journal = journal
        self.runner: CommandRunner = runner or subprocess.run
        self.name = settings.model

    def _environment(self) -> dict[str, str]:
        env = dict(os.environ)
        # Do not accidentally select an API-billed or injected workload credential.
        for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "CODEX_ACCESS_TOKEN"):
            env.pop(key, None)
        return env

    def _run(self, args: list[str], *, input_text: str = "", timeout: int | None = None):
        return self.runner(
            args,
            input=input_text,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout or self.settings.timeout_s,
            env=self._environment(),
        )

    def _check_auth(self) -> None:
        if not self.settings.require_chatgpt_auth:
            return
        result = self._run(
            [self.settings.codex_binary, "login", "status"],
            timeout=min(self.settings.timeout_s, 30),
        )
        status = (result.stdout or "") + "\n" + (result.stderr or "")
        if result.returncode != 0 or "Logged in using ChatGPT" not in status:
            raise PermissionError("Codex CLI must be signed in with ChatGPT for this transport")

    @staticmethod
    def _usage(events: str) -> dict[str, int]:
        completed = []
        for line in events.splitlines():
            if not line.strip():
                continue
            event = loads(line)
            if not isinstance(event, dict):
                raise ValueError("Codex emitted a non-object event")
            if event.get("type") == "turn.completed":
                completed.append(event)
        if len(completed) != 1 or not isinstance(completed[0].get("usage"), dict):
            raise ValueError("Codex did not emit exactly one completed turn with usage")
        usage = completed[0]["usage"]
        result = {}
        for key in (
            "input_tokens",
            "cached_input_tokens",
            "output_tokens",
            "reasoning_output_tokens",
        ):
            if key in usage:
                result[key] = integer(usage[key])
        if "input_tokens" not in result or "output_tokens" not in result:
            raise ValueError("Codex usage omitted required token counts")
        return result

    def call(self, call_id: str, role: str, instruction: str, context: dict,
             images: list[ImageInput], schema: dict) -> dict[str, Any]:
        s = self.settings
        if context.get("episode") != self.journal.episode:
            raise ValueError("Model context belongs to another episode")
        validate_images(images, self.journal.episode,
                        max_images=s.max_images, max_pixels=s.max_pixels)
        text(instruction, "system instruction", 32000)
        if len(dumps(context)) > 256_000:
            raise ValueError("Context metadata too large")
        self._check_auth()
        packet = {
            "instruction": instruction,
            "context": context,
            "images": [dict(ordinal=n, **image.metadata()) for n, image in enumerate(images)],
            "response_contract": "Return only one JSON value matching the supplied schema.",
        }
        manifest = {
            "model": s.model,
            "transport": "codex_exec",
            "billing_route": "chatgpt_subscription",
            "usd_cost_accounting": "unavailable_not_zero_compute",
            "instruction": instruction,
            "context": context,
            "images": [image.metadata() for image in images],
            "schema": schema,
            "reasoning_effort": s.reasoning_effort,
            "timeout_s": s.timeout_s,
            "wire_sha256": digest(packet),
            "ephemeral": True,
            "sandbox": "read-only",
            "minimal_agent_context": s.minimal_agent_context,
        }
        # Zero is the API-dollar reservation. The journal still enforces call count.
        self.journal.reserve(call_id, role, manifest, 0)
        start = time.monotonic()
        try:
            with tempfile.TemporaryDirectory(prefix="physical-harness-codex-") as directory:
                root = Path(directory)
                schema_path = root / "schema.json"
                output_path = root / "result.json"
                schema_path.write_bytes(dumps(schema))
                instructions_path = root / "minimal-instructions.md"
                image_paths = []
                for index, image in enumerate(images):
                    suffix = ".png" if image.uri.endswith(".png") else ".jpg"
                    path = root / f"image-{index:02d}{suffix}"
                    path.write_bytes(image.data)
                    image_paths.append(path)
                command = [
                    s.codex_binary,
                    "exec",
                    "--ephemeral",
                    "--sandbox",
                    "read-only",
                    "--skip-git-repo-check",
                    "--ignore-user-config",
                    "--ignore-rules",
                    "--strict-config",
                    "--cd",
                    str(root),
                    "--model",
                    s.model,
                ]
                if s.reasoning_effort:
                    command += ["-c", f'model_reasoning_effort="{s.reasoning_effort}"']
                if s.minimal_agent_context:
                    instructions_path.write_text(
                        "Answer the supplied task directly. Do not use tools. "
                        "Return only the requested structured output.\n"
                    )
                    command += [
                        "-c",
                        'personality="none"',
                        "-c",
                        "model_instructions_file=" + dumps(str(instructions_path)).decode(),
                    ]
                    for feature in _MINIMAL_CODEX_DISABLED_FEATURES:
                        command += ["--disable", feature]
                for path in image_paths:
                    command += ["--image", str(path)]
                command += [
                    "--output-schema",
                    str(schema_path),
                    "--output-last-message",
                    str(output_path),
                    "--json",
                    "-",
                ]
                result = self._run(command, input_text=dumps(packet).decode())
                seconds = time.monotonic() - start
                if result.returncode != 0:
                    raise RuntimeError("codex exec failed")
                if len(result.stdout.encode()) > s.max_output_bytes:
                    raise ValueError("Codex event stream exceeds its byte bound")
                if not output_path.is_file() or output_path.stat().st_size > s.max_output_bytes:
                    raise ValueError("Codex final output is missing or exceeds its byte bound")
                usage = self._usage(result.stdout)
                value = loads(output_path.read_bytes())
                validate_schema(value, schema)
            self.journal.complete(
                call_id,
                {
                    "billing_route": "chatgpt_subscription",
                    "api_microusd": 0,
                    "usage": usage,
                    "seconds": seconds,
                    "completed": True,
                },
                0,
            )
            return value
        except Exception as exc:
            self.journal.fail(call_id, type(exc).__name__)
            raise


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
