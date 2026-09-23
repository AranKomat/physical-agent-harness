"""Explicitly enabled HTTP with per-call process deadlines and no retry/fallback."""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from urllib.parse import urlsplit

from physical_harness.integrations.experiment.validation import dumps, integer, loads, number, text


class TransportFailure(RuntimeError):
    """Remote inference may still be running/billed after this failure."""


@dataclass(frozen=True)
class HttpTransport:
    base_url: str
    api_key_env: str | None
    allow_network: bool = False
    allow_local_http: bool = False
    timeout_s: float = 120.0
    max_response_bytes: int = 4_000_000

    def __post_init__(self):
        url = urlsplit(self.base_url)
        local = url.hostname in {"localhost", "127.0.0.1", "::1"}
        if url.username or url.password or url.query or url.fragment or not url.netloc:
            raise ValueError("Plain operator-configured base URL required")
        if url.scheme != "https" and not (url.scheme == "http" and local and self.allow_local_http):
            raise ValueError("HTTPS required, except explicitly permitted loopback HTTP")
        number(self.timeout_s, minimum=0.01)
        integer(self.max_response_bytes, minimum=1)
        if self.api_key_env is not None:
            text(self.api_key_env, "key environment variable", 128)

    def post(self, path: str, payload: dict) -> dict:
        if not self.allow_network:
            raise PermissionError("Model transport disabled; require explicit network opt-in")
        if path not in {"/responses", "/responses/input_tokens", "/chat/completions"}:
            raise ValueError("Unapproved endpoint")
        headers = {"Content-Type": "application/json"}
        if self.api_key_env:
            key = os.environ.get(self.api_key_env)
            if not key:
                raise ValueError("Configured API credential environment variable is unset")
            headers["Authorization"] = "Bearer " + key
        request = {"url": self.base_url.rstrip("/") + path, "headers": headers,
                   "payload": payload, "timeout_s": self.timeout_s,
                   "max_response_bytes": self.max_response_bytes}
        body = dumps(request)
        if len(body) > 40_000_000:
            raise ValueError("HTTP request too large")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "physical_harness.integrations.experiment.http_worker"],
                input=body, capture_output=True, timeout=self.timeout_s, check=False)
        except subprocess.TimeoutExpired as exc:
            raise TransportFailure("Local HTTP deadline; remote status unknown") from exc
        if result.returncode != 0 or len(result.stdout) > self.max_response_bytes + 4096:
            raise TransportFailure("HTTP worker failed")
        reply = loads(result.stdout)
        if "error" in reply:
            raise TransportFailure("HTTP request failed; no automatic retry")
        if reply.get("status") != 200 or not isinstance(reply.get("body"), dict):
            raise TransportFailure("Unexpected HTTP response")
        return reply["body"]
