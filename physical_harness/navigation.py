from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Any, Mapping

import networkx as nx


@dataclass(frozen=True)
class PlaceNode:
    place_id: str
    label: str
    kind: str  # room | corridor | doorway | elevator | workcell | landmark
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlaceEdge:
    a: str
    b: str
    traversable: bool = True
    gateway_entity: str | None = None
    cost: float = 1.0


class TopologicalMap:
    """Semantic layer above a metric occupancy map.

    GPT reasons about places/gateways. A normal navigation stack owns metric
    localization, path planning, and obstacle avoidance.
    """

    def __init__(self):
        self.nodes: dict[str, PlaceNode] = {}
        self.edges: list[PlaceEdge] = []
        self.gateway_states: dict[str, str] = {}
        self.gateway_evidence: dict[str, tuple[str, ...]] = {}

    def upsert_node(self, node: PlaceNode) -> None:
        self.nodes[node.place_id] = node

    def add_edge(self, edge: PlaceEdge) -> None:
        if edge.a not in self.nodes or edge.b not in self.nodes:
            raise ValueError("Both places must exist before adding an edge")
        if not math.isfinite(edge.cost) or edge.cost <= 0:
            raise ValueError("Edge cost must be finite and positive")
        self.edges.append(edge)

    def neighbors(self, place_id: str) -> list[PlaceEdge]:
        return [e for e in self.edges if e.a == place_id or e.b == place_id]

    def update_gateway(self, entity_id: str, state: str, evidence_ids: tuple[str, ...]) -> None:
        """Apply an observed door state, never an open/close command."""
        if state not in {"open", "closed", "unknown"} or not evidence_ids:
            raise ValueError("Gateway updates require a valid state and evidence")
        if not any(e.gateway_entity == entity_id for e in self.edges):
            raise KeyError(entity_id)
        self.gateway_states[entity_id] = state
        self.gateway_evidence[entity_id] = tuple(evidence_ids)
        self.edges = [
            replace(e, traversable=state == "open") if e.gateway_entity == entity_id else e
            for e in self.edges
        ]

    def route(
        self, start: str, goal: str, *, include_blocked: bool = False
    ) -> list[PlaceEdge] | None:
        graph = nx.Graph()
        graph.add_nodes_from(self.nodes)
        for edge in self.edges:
            if not include_blocked and (
                not edge.traversable
                or (
                    edge.gateway_entity is not None
                    and self.gateway_states.get(edge.gateway_entity) != "open"
                )
            ):
                continue
            if not graph.has_edge(edge.a, edge.b) or edge.cost < graph[edge.a][edge.b]["weight"]:
                graph.add_edge(edge.a, edge.b, weight=edge.cost, edge=edge)
        try:
            nodes = nx.shortest_path(graph, start, goal, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
        return [graph[a][b]["edge"] for a, b in zip(nodes, nodes[1:])]
