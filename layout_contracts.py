"""Flat value types for the layout pipeline.

These types describe the data passed between the pipeline stages defined in
``CLEAN_REWRITE_IMPLEMENTATION_PLAN.md``:

    request = LayoutRequest.from_command(...)
    scope = build_scope(request, graph)
    prepared = prepare_graph(scope, graph)
    result = layout_engine.layout(prepared, graph)

``LayoutRequest`` describes user intent. ``LayoutScope`` describes the resolved
participating set before topology mutation. ``PreparedScope`` is the
authoritative post-mutation input to layout, apply, state-sync, and push.
``LayoutResult`` is what the engine returns.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class LayoutRequest:
    """What the user asked for.

    Plain values only — no live derived graph data lives here. Each public
    command in ``node_layout`` constructs one of these and hands it to the
    shared orchestrator.
    """
    command: str
    scheme_multiplier: Optional[float]
    undo_label: str
    scope_kind: str
    routing_mode: str = "full"
    selected_horizontal_side_mode: Optional[str] = None
    scale_axis: Optional[str] = None


@dataclass
class LayoutScope:
    """Resolved command scope before topology preparation.

    Built by ``layout_scope.build_scope``; consumed by ``layout_prepare``.
    Anything here that can be invalidated by routing-dot insertion (node
    sets, filters, scale tables) must be re-resolved during preparation.
    """
    request: LayoutRequest
    roots: list
    initial_nodes: set
    node_filter: Optional[set]
    bbox_before: Optional[tuple]
    freeze_blocks: list
    freeze_dimension_overrides: dict
    freeze_non_root_ids: set
    freeze_member_ids: set
    packer_params: dict = field(default_factory=dict)


@dataclass
class PreparedScope:
    """Authoritative post-preparation input to layout and mutation stages.

    Produced by ``layout_prepare.prepare_graph``. ``layout_nodes`` is the set
    that the engine may traverse; ``state_nodes`` is the set eligible for
    hidden-state persistence; ``push_subject_nodes`` is the set used for the
    final room-push.
    """
    request: LayoutRequest
    roots: list
    node_filter: Optional[set]
    layout_nodes: set
    state_nodes: set
    push_subject_nodes: set
    bbox_before: Optional[tuple]
    freeze_blocks: list
    freeze_dimension_overrides: dict
    freeze_member_ids: set
    per_node_scheme: dict
    per_node_h_scale: dict
    per_node_v_scale: dict
    packer_params: dict = field(default_factory=dict)


@dataclass
class LayoutResult:
    """Geometry result returned by the engine.

    ``mode_assignments`` records which mode actually placed each node (e.g.
    ``"horizontal"``). It is layout metadata; the per-command write-back
    policy in ``layout_state_sync`` decides what gets persisted.
    """
    subtrees: list
    placed_nodes: set
    mode_assignments: dict
    state_updates: dict = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)
