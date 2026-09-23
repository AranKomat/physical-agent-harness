"""Receipt-based compute accounting; low call count is not the optimization objective.

Token/pixel counts are workload measurements, not semantic information estimates.
Prices are not hard-coded. Missing usage or energy stays unknown, never zero.
"""
from __future__ import annotations

from dataclasses import dataclass

from physical_harness.core.actions import digest, ids, integer, number, plain, text
from physical_harness.perception.contracts import FrameRef


@dataclass(frozen=True)
class ComputeReceipt:
    id: str
    role: str
    model: str
    request_fingerprint: str
    status: str
    start_wall: float
    end_wall: float
    input_tokens: int | None = None
    cached_input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_output_tokens: int | None = None  # Subset of output when provider documents this.
    actual_microusd: int | None = None
    input_image_ids: tuple[str, ...] = ()
    image_contents: tuple[str, ...] = ()
    image_pixels: tuple[int, ...] = ()
    inference_seconds: float | None = None
    queue_seconds: float | None = None
    output_includes_reasoning: bool = True

    def __post_init__(self):
        for s in (self.id, self.role, self.model, self.request_fingerprint):
            text(s)
        if self.status not in {"completed", "failed", "unknown"}:
            raise ValueError("Unknown compute outcome")
        number(self.start_wall, low=0)
        number(self.end_wall, low=self.start_wall)
        for v in (self.input_tokens, self.cached_input_tokens, self.output_tokens,
                  self.reasoning_output_tokens, self.actual_microusd):
            if v is not None:
                integer(v, high=10**12)
        if self.cached_input_tokens is not None and (self.input_tokens is None or self.cached_input_tokens > self.input_tokens):
            raise ValueError("Cached-input count must be a subset of total input")
        if type(self.output_includes_reasoning) is not bool:
            raise ValueError("Explicit reasoning accounting convention required")
        if self.output_includes_reasoning and self.reasoning_output_tokens is not None and (
            self.output_tokens is None or self.reasoning_output_tokens > self.output_tokens
        ):
            raise ValueError("Reasoning count cannot exceed inclusive output count")
        ids(self.input_image_ids, limit=32)
        if type(self.image_contents) is not tuple or type(self.image_pixels) is not tuple or not (
            len(self.input_image_ids) == len(self.image_contents) == len(self.image_pixels)
        ):
            raise ValueError("Image IDs/hashes/pixel counts must align")
        from physical_harness.perception.contracts import sha256
        for s, p in zip(self.image_contents, self.image_pixels):
            sha256(s)
            integer(p, low=1, high=268435456)
        for v in (self.inference_seconds, self.queue_seconds):
            if v is not None:
                number(v, low=0)
        if self.inference_seconds is not None and self.queue_seconds is not None and self.inference_seconds+self.queue_seconds > self.end_wall-self.start_wall+1e-6:
            raise ValueError("Latency breakdown exceeds measured total")


class ComputeLedger:
    def __init__(self, journal):
        self.journal = journal

    def add(self, receipt: ComputeReceipt):
        if not isinstance(receipt, ComputeReceipt):
            raise ValueError("ComputeReceipt required")
        body = plain(receipt)
        body["receipt_id"] = body.pop("id")
        self.journal.put("embodied_compute", receipt.id, body)

    def report(self) -> dict:
        grouped = {}
        seen_content = set()
        for r in self.journal.records("embodied_compute"):
            key = r["role"]
            g = grouped.setdefault(key, {"calls": 0, "input_tokens_known": 0, "cached_input_tokens_known": 0,
                                        "output_tokens_known": 0, "reasoning_tokens_known": 0,
                                        "microusd_known": 0, "missing_usage_calls": 0, "missing_cost_calls": 0,
                                        "wall_seconds_sum": 0., "pixels_sent": 0,
                                        "first_seen_content_pixels": 0, "repeated_content_pixels": 0,
                                        "failed_or_unknown_calls": 0})
            g["calls"] += 1
            g["failed_or_unknown_calls"] += r["status"] != "completed"
            g["wall_seconds_sum"] += r["end_wall"]-r["start_wall"]
            for field, out in (("input_tokens", "input_tokens_known"), ("cached_input_tokens", "cached_input_tokens_known"),
                               ("output_tokens", "output_tokens_known"), ("reasoning_output_tokens", "reasoning_tokens_known"),
                               ("actual_microusd", "microusd_known")):
                if r[field] is not None:
                    g[out] += r[field]
            g["missing_usage_calls"] += r["input_tokens"] is None or r["output_tokens"] is None
            g["missing_cost_calls"] += r["actual_microusd"] is None
            for sha, pixels in zip(r["image_contents"], r["image_pixels"]):
                g["pixels_sent"] += pixels
                # Per-role exact content novelty, not latent feature reuse or semantic change.
                k = key, sha
                g["repeated_content_pixels" if k in seen_content else "first_seen_content_pixels"] += pixels
                seen_content.add(k)
        return {"roles": grouped,
                "notes": ["Output and reasoning counts are not added when reasoning is a subset.",
                          "Wall sums can overlap for concurrent calls; not elapsed episode time.",
                          "First-seen image bytes are a proxy, not novel physical information.",
                          "GPU energy comes from the existing measured energy path, not token/share estimates."]}


def receipt_images(frames: tuple[FrameRef, ...]):
    return {"input_image_ids": tuple(f.asset_id for f in frames),
            "image_contents": tuple(f.content_sha256 for f in frames),
            "image_pixels": tuple(f.pixels for f in frames)}


def from_existing_model_call(row: dict, *, receipt_id: str, role: str, model: str,
                             frames: tuple[FrameRef, ...], start_wall: float, end_wall: float) -> ComputeReceipt:
    """Explicit normalized transport receipt -> accounting. Unknown keys are not guessed.

    Caller obtains normalized usage from the existing model adapter. No model API
    request, price lookup, benchmark score, or hidden reasoning content is used.
    """
    if type(row) is not dict or set(row) - {"input_tokens", "cached_input_tokens", "output_tokens",
                                         "reasoning_output_tokens", "actual_microusd", "status"}:
        raise ValueError("Use explicit normalized provider usage fields")
    usage = {k:v for k,v in row.items() if k != "status"}
    return ComputeReceipt(receipt_id, role, model, digest([receipt_id, [f.content_sha256 for f in frames]]),
                          row.get("status", "unknown"), start_wall, end_wall, **usage, **receipt_images(frames))
