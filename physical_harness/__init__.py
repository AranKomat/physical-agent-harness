"""Physical-agent harness reference scaffold.

This package is intentionally benchmark/model agnostic. It provides typed
contracts and orchestration glue; perception, navigation, policy inference,
and robot control remain adapters.
"""

from physical_harness.core.contracts import (
    NavigationReceipt,
    NavigationRequest,
    SkillReceipt,
    SkillRequest,
    VerificationRequest,
    VerificationResult,
    VerificationVerdict,
)
from physical_harness.core.events import EventType, RuntimeEvent
from physical_harness.perception.localization import LocalizationLost, RGBDOdometry
from physical_harness.reasoning.runtime import HarnessRuntime

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
    "RGBDOdometry",
    "LocalizationLost",
]
