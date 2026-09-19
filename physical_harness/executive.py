"""Sparse executive dispatch. No provider SDK or paid calls are enabled here."""

from __future__ import annotations

import json
from typing import Any, Callable, Mapping

from .backends.base import ExecutiveBackend
from .contracts import RuntimeEvent

SEMANTIC_TOOLS = frozenset(
    {
        "inspect",
        "navigate_to",
        "run_skill",
        "execute_l3",
        "request_verification",
        "finish",
        "stop",
    }
)


class ExecutiveLoop:
    def __init__(
        self,
        episode_id: str,
        executive: ExecutiveBackend,
        context: Callable[[RuntimeEvent], Mapping[str, Any]],
        handlers: Mapping[str, Callable[[Mapping[str, Any]], Any]],
        *,
        can_finish: Callable[[], bool],
        on_decision: Callable[[RuntimeEvent, Mapping[str, Any]], None] | None = None,
        max_decisions: int = 20,
        max_context_bytes: int = 12000,
    ):
        if set(handlers) - SEMANTIC_TOOLS:
            raise ValueError("Only semantic tools are allowed")
        if max_decisions < 1 or max_context_bytes < 1:
            raise ValueError("Positive executive budgets required")
        self.episode_id, self.executive = episode_id, executive
        self.context, self.handlers, self.can_finish = context, dict(handlers), can_finish
        self.on_decision = on_decision
        self.max_decisions, self.max_bytes = max_decisions, max_context_bytes
        self.calls = 0
        self._seen: set[str] = set()
        self.finished = False
        self.trace: list[dict[str, Any]] = []

    def on_event(self, event: RuntimeEvent) -> Any:
        if event.episode_id != self.episode_id:
            raise ValueError("Foreign episode event")
        if self.finished or event.event_id in self._seen:
            return None
        if self.calls >= self.max_decisions:
            raise RuntimeError("Executive decision budget exhausted")
        context = dict(self.context(event))
        if len(json.dumps(context, allow_nan=False).encode()) > self.max_bytes:
            raise ValueError("Executive context exceeds byte budget")
        # Reserve before invoking the provider. An ambiguous failure is not retried
        # automatically, and a duplicate event must not execute physical work twice.
        self._seen.add(event.event_id)
        self.calls += 1
        decision = self.executive.decide(context)
        if not isinstance(decision, Mapping) or not {"tool", "arguments"} <= set(decision):
            raise ValueError("Executive must return tool and arguments")
        if set(decision) - {"tool", "arguments", "information_need"}:
            raise ValueError("Executive returned unsupported decision metadata")
        tool, arguments = decision["tool"], decision["arguments"]
        if not isinstance(tool, str) or tool not in self.handlers or tool not in SEMANTIC_TOOLS:
            raise ValueError("Unsupported semantic tool")
        if not isinstance(arguments, Mapping):
            raise ValueError("Tool arguments must be an object")
        if len(json.dumps(arguments, allow_nan=False).encode()) > 8192:
            raise ValueError("Tool arguments exceed limit")
        if self.on_decision is not None:
            self.on_decision(event, decision)
        if tool == "finish" and not self.can_finish():
            raise ValueError("Finish requires verified tasks and resolved execution")
        result = self.handlers[tool](arguments)
        trace = {"event_id": event.event_id, "tool": tool, "arguments": dict(arguments)}
        if "information_need" in decision:
            trace["information_need"] = dict(decision["information_need"])
        self.trace.append(trace)
        if tool in {"finish", "stop"}:
            self.finished = True
        return result
