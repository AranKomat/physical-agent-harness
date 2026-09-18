"""Physical-agent harness reference scaffold.

This package is intentionally benchmark/model agnostic. It provides typed
contracts and orchestration glue; perception, navigation, policy inference,
and robot control remain adapters.
"""

from .contracts import (
    EventType,
    NavigationReceipt,
    NavigationRequest,
    RuntimeEvent,
    SkillReceipt,
    SkillRequest,
    VerificationRequest,
    VerificationResult,
    VerificationVerdict,
)
from .runtime import HarnessRuntime

__all__ = [
    "RuntimeEvent",
    "EventType",
    "SkillRequest",
    "SkillReceipt",
    "VerificationRequest",
    "VerificationResult",
    "VerificationVerdict",
    "NavigationRequest",
    "NavigationReceipt",
    "HarnessRuntime",
]
