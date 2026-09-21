"""Opt-in, simulator-only phase handoffs. Importing this package never starts work."""
from .contracts import (
    Check,
    GateReport,
    Phase,
    PolicyIdentity,
    Qualification,
    Regime,
    ResetReceipt,
    ResetRequest,
    Route,
    Snapshot,
)
from .executor import Backend, HybridExecutor
from .integration import (
    ablation_routes,
    journal_sink,
    policy_exposure_diagnostic_routes,
    wrap_native,
)
from .staging import (
    StagingCandidate,
    StagingConfig,
    StagingPlan,
    TargetPoint,
    resolve_staging_pose,
    target_from_depth_pixel,
)
from .telemetry import HandoffTelemetry, PausedWorldComparison, paused_world_compatibility

__all__ = ["Backend", "Check", "GateReport", "HybridExecutor", "Phase", "PolicyIdentity",
           "Qualification", "Regime", "ResetReceipt", "ResetRequest", "Route", "Snapshot",
           "HandoffTelemetry", "PausedWorldComparison", "StagingCandidate", "StagingConfig",
           "StagingPlan", "TargetPoint", "ablation_routes", "journal_sink",
           "paused_world_compatibility", "policy_exposure_diagnostic_routes",
           "resolve_staging_pose", "target_from_depth_pixel", "wrap_native"]
