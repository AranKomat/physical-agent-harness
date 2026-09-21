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
from .integration import ablation_routes, journal_sink, wrap_native

__all__ = ["Backend", "Check", "GateReport", "HybridExecutor", "Phase", "PolicyIdentity",
           "Qualification", "Regime", "ResetReceipt", "ResetRequest", "Route", "Snapshot",
           "ablation_routes", "journal_sink", "wrap_native"]
