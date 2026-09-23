"""Additive multimodal episodic memory prototype; disabled until explicitly wired.

No imports of robot controllers, WorldState, TaskLedger, model SDKs or GPU runtimes.
"""
from physical_harness.world.memory.integration import (
           DecisionCutoffLog,
           MemoryDecision,
           MemorySidecar,
)
from physical_harness.world.memory.retrieval import Retriever, attach_memory
from physical_harness.world.memory.schemas import Asset, Card, Cutoff, Draft, PacketBudget
from physical_harness.world.memory.selection import (
           Boundary,
           EventRecorder,
           RecentBuffer,
           boundary_from_runtime,
)
from physical_harness.world.memory.spatial_views import (
           CoverageObservation,
           PosedRGBDKeyframe,
           SpatialViewIndex,
)
from physical_harness.world.memory.store import MemoryStore
from physical_harness.world.memory.writer import AsyncAnnotator, parse_draft

__all__ = ['Asset', 'Card', 'Cutoff', 'Draft', 'PacketBudget', 'MemoryStore',
           'Boundary', 'EventRecorder', 'RecentBuffer', 'boundary_from_runtime',
           'Retriever', 'attach_memory', 'AsyncAnnotator', 'parse_draft',
           'DecisionCutoffLog', 'MemoryDecision', 'MemorySidecar',
           'CoverageObservation', 'PosedRGBDKeyframe', 'SpatialViewIndex']
