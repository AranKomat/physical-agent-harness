from __future__ import annotations

from typing import Any, Mapping, Protocol

from ..contracts import (
    NavigationReceipt,
    NavigationRequest,
    SkillReceipt,
    SkillRequest,
    VerificationRequest,
    VerificationResult,
)


class MotorBackend(Protocol):
    name: str

    def run_skill(self, request: SkillRequest) -> SkillReceipt: ...


class NavigationBackend(Protocol):
    name: str

    def navigate(self, request: NavigationRequest) -> NavigationReceipt: ...


class DirectControlBackend(Protocol):
    name: str

    def execute(self, instruction: Mapping[str, Any]) -> SkillReceipt: ...


class WorldModelBackend(Protocol):
    name: str

    def query(self, query: Mapping[str, Any]) -> Mapping[str, Any]: ...
    def predicate_confidence(self, predicate: str) -> float | None: ...


class VerifierBackend(Protocol):
    name: str

    def verify(self, request: VerificationRequest) -> VerificationResult: ...


class ExecutiveBackend(Protocol):
    name: str

    def decide(self, context: Mapping[str, Any]) -> Mapping[str, Any]: ...
