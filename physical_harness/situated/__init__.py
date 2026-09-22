"""Opt-in situated execution. Importing never loads SAM, calls models or moves robots."""
from .contracts import Binding, Capability, Effect, Fact, FactPacket, ScopeBudget
from .graph import Graph, Node
from .graph_runtime import GraphSession, Handler, NodeContext, NodeResult
from .identity import AssociationProof, IdentityLedger, SemanticClaim, Tracklet
from .inspection import InspectionCandidate, inspection_program, orbit_views, rank_inspections
from .integration import CatalogActionHandler, identity_binding
from .monitor import MonitorVerdict, ProgressMonitor
from .motion import MotionLimits, PoseAnchor, motion_program, proposal_schema
from .programs import catalog_for_programs, enforce_extra_step_checks
from .visual import GoalKind, VisualAsset, VisualGoal, VisualRole, monitor_packet

__all__ = [
    "AssociationProof", "Binding", "Capability", "CatalogActionHandler", "Effect", "Fact",
    "FactPacket", "GoalKind", "Graph", "GraphSession", "Handler", "IdentityLedger",
    "InspectionCandidate", "MonitorVerdict", "MotionLimits", "Node", "NodeContext", "NodeResult",
    "PoseAnchor", "ProgressMonitor", "ScopeBudget", "SemanticClaim", "Tracklet", "VisualAsset",
    "VisualGoal", "VisualRole", "catalog_for_programs", "enforce_extra_step_checks",
    "identity_binding", "inspection_program", "monitor_packet", "motion_program", "orbit_views",
    "proposal_schema", "rank_inspections",
]
