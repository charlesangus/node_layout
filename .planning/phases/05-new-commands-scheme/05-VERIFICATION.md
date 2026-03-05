---
phase: 05-new-commands-scheme
verified: 2026-03-05T06:02:13Z
status: passed
score: 3/3 success criteria verified
re_verification:
  previous_status: passed
  previous_score: 10/10
  gaps_closed: []
  gaps_remaining: []
  regressions: []
  notes: "Re-verification covers plans 05-03 and 05-04 (gap-closure plans added after initial verification) and uses the canonical three success criteria supplied by the orchestrator."
---

# Phase 05: New Commands Scheme — Verification Report

**Phase Goal:** Users have two new scaling commands and a compact-scheme layout option that apply the existing layout engine with different spacing policies
**Verified:** 2026-03-05T06:02:13Z
**Status:** PASSED
**Re-verification:** Yes — after plans 05-03 and 05-04 were added as gap-closure plans

---

## Goal Achievement

### Observable Truths (Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Selecting nodes and invoking "Shrink/Expand Selected" scales spacing between those nodes centered on the root node, without affecting unselected nodes | VERIFIED | `_scale_selected_nodes` iterates only `nuke.selectedNodes()` (line 701); anchor = `max(selected_nodes, key=lambda n: (n.ypos(), -n.xpos()))` (line 705); all other nodes untouched |
| 2 | Invoking "Scale Upstream" from a selected node applies the same shrink/expand scaling to all upstream nodes in the tree | VERIFIED | `_scale_upstream_nodes` calls `collect_subtree_nodes(anchor_node)` (line 734); no layout engine calls; `shrink_upstream`/`expand_upstream` use `SHRINK_FACTOR=0.8`/`EXPAND_FACTOR=1.25` |
| 3 | Invoking "Compact Layout" runs the full layout algorithm but applies tight spacing throughout — result is visually denser than Normal | VERIFIED | `layout_upstream_compact` calls `layout_upstream(scheme_multiplier=compact_multiplier)` (line 685); `vertical_gap_between` formula `int(loose_gap_multiplier * scheme_multiplier * snap_threshold)` produces smaller values when `scheme_multiplier=0.6`; `TestSchemeDifferentiation.test_vertical_gap_compact_smaller_than_normal` confirms numerically; 121 tests pass |

**Score:** 3/3 success criteria verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `node_layout.py` | Scheme-aware layout engine with 10 public entry-points, fixed scaling helpers | VERIFIED | All 10 exports confirmed: `layout_upstream`, `layout_selected`, `layout_upstream_compact`, `layout_selected_compact`, `layout_upstream_loose`, `layout_selected_loose`, `shrink_selected`, `expand_selected`, `shrink_upstream`, `expand_upstream`; `SHRINK_FACTOR=0.8`, `EXPAND_FACTOR=1.25` at module level (lines 680-681); `side_margins_h`/`side_margins_v` split in both `compute_dims` (lines 281-282) and `place_subtree` (lines 401-402) |
| `menu.py` | 8 new menu command registrations in correct separator sections | VERIFIED | 19 total `addCommand` calls; all 8 new commands registered with correct shortcuts; `Compact`/`Loose` variants have no shortcuts; `Shrink`/`Expand` use `ctrl+,`/`ctrl+.`/`ctrl+shift+,`/`ctrl+shift+.`; valid Python (ast.parse passes) |
| `tests/test_prefs_integration.py` | Behavioral and AST tests for scheme differentiation, scaling, and horizontal-only scheme fix | VERIFIED | Five test classes: `TestPrefsIntegration`, `TestSchemeMultiplierPipeline`, `TestGeometricScalingCommands`, `TestSchemeDifferentiation`, `TestHorizontalOnlyScheme`; 121 tests, 0 failures |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `layout_upstream_compact` | `layout_upstream` | `scheme_multiplier=prefs_singleton.get("compact_multiplier")` | WIRED | Line 685: exact call confirmed |
| `vertical_gap_between` | `int(loose_gap_multiplier * scheme_multiplier * snap_threshold)` | `scheme_multiplier` parameter | WIRED | Line 92: formula confirmed; `scheme_multiplier=None` defaults to `normal_multiplier` (line 90) |
| `shrink_selected` | `_scale_selected_nodes(SHRINK_FACTOR)` | undo-group wrapper | WIRED | Line 754: call confirmed; try/except/else undo pattern at lines 748-759 |
| `shrink_upstream` | `_scale_upstream_nodes(SHRINK_FACTOR)` via `collect_subtree_nodes` | undo-group wrapper with `nuke.selectedNode()` guard | WIRED | Lines 776-789: guard, undo begin, call, undo end/cancel confirmed |
| `menu.py` | `node_layout.layout_upstream_compact` | `layout_menu.addCommand` | WIRED | Line 22 of menu.py confirmed |
| `menu.py` | `node_layout.shrink_selected` | `layout_menu.addCommand` with `ctrl+,` | WIRED | Lines 32-37 of menu.py confirmed |
| `compute_dims` | `side_margins_h` (horizontal, `normal_multiplier`) | explicit `mode_multiplier=normal_multiplier` | WIRED | Line 281: horizontal width formula uses `side_margins_h`; line 316 staircase uses `side_margins_v` |
| `layout_selected horizontal_clearance` | `normal_multiplier` | `prefs_singleton.get("normal_multiplier")` | WIRED | Line 656: formula uses `normal_multiplier` directly, not `resolved_scheme_multiplier`; confirmed by `TestHorizontalOnlyScheme.test_horizontal_clearance_does_not_use_resolved_scheme_multiplier` |

---

### Requirements Coverage

Requirements declared across all four plans: CMD-01, CMD-02, SCHEME-01 (plans 05-01 through 05-04 all reference the same three IDs).

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CMD-01 | 05-01, 05-02, 05-04 | Shrink/expand selected nodes command scales the spacing between selected nodes up or down, centered on the root node | SATISFIED | `shrink_selected`/`expand_selected` at lines 748-773; center-based offset arithmetic with tiebreaker anchor and snap_min floor; registered in menu.py with `ctrl+,`/`ctrl+.` shortcuts |
| CMD-02 | 05-01, 05-02, 05-04 | Scale upstream command applies the same shrink/expand scaling to all upstream nodes from the selected node | SATISFIED | `shrink_upstream`/`expand_upstream` at lines 776-805; `_scale_upstream_nodes` uses `collect_subtree_nodes`; registered in menu.py with `ctrl+shift+,`/`ctrl+shift+.` |
| SCHEME-01 | 05-01, 05-02, 05-03 | Compact layout scheme produces the same structure as standard layout but applies tight spacing throughout regardless of node color or category | SATISFIED | `layout_upstream_compact`/`layout_selected_compact` call base functions with `compact_multiplier` (0.6); `scheme_multiplier` propagates through `compute_dims` and `place_subtree`; vertical gaps tighter, horizontal gaps unchanged; `TestSchemeDifferentiation` confirms compact < normal < loose numerically |
| PREFS-04 | 05-01, 05-02, 05-03 | Three presets available: Compact, Normal (default), Loose — each sets all spacing values at once | SATISFIED (cross-phase) | Phase 4 VERIFICATION declared NOT SATISFIED (preset commands deferred to Phase 5 per CONTEXT.md). Phase 5 delivered `layout_upstream_compact`, `layout_selected_compact`, `layout_upstream_loose`, `layout_selected_loose` registered in `menu.py` (lines 22-30); all three scheme variants wired through `prefs_singleton.get("compact_multiplier")`/`normal_multiplier`/`loose_multiplier` at call time. Functionally satisfies PREFS-04 intent. |

No orphaned requirements: REQUIREMENTS.md traceability table maps CMD-01, CMD-02, SCHEME-01 to Phase 5 and PREFS-04 to Phase 4 → Phase 5; all marked Complete.

---

### Plan Evolution Note

Plans 05-03 and 05-04 were gap-closure plans added after the initial verification. They refined the 05-01/05-02 implementation:

- **05-03** split `side_margins` into `side_margins_h` (always uses `normal_multiplier`) and `side_margins_v` (uses `scheme_multiplier`) in both `compute_dims` and `place_subtree`, and changed `horizontal_clearance` in `layout_selected` from `resolved_scheme_multiplier` to `normal_multiplier`. This supersedes plan 05-01 truth #4 — the horizontal clearance intentionally uses `normal_multiplier`, not `scheme_multiplier`. This is the correct design: compact/loose schemes affect only vertical spacing.
- **05-04** fixed `_scale_selected_nodes` and `_scale_upstream_nodes` to use center-based offsets (accounting for `screenWidth()/2`), `round()` instead of `int()`, an anchor tiebreaker `(n.ypos(), -n.xpos())`, and a `snap_min` floor in `_scale_selected_nodes`. This is the correct implementation for CMD-01/CMD-02 and supersedes the 05-01 implementation of those helpers.

Both refinements are implemented correctly and fully tested.

---

### Anti-Patterns Found

Scanned `node_layout.py` and `menu.py` for TODO/FIXME, empty returns, placeholder comments.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | No anti-patterns found |

The `return []` instances noted in the prior verification (in `_get_input_slot_pairs` and `get_inputs` guard clauses) remain intentional early returns, not stubs.

---

### Human Verification Required

Three items cannot be verified programmatically and require manual testing inside Nuke.

#### 1. Compact vs Normal vs Loose visual spacing difference

**Test:** Build a 5-node chain (e.g. Grade feeding into Blur into Merge into Grade into Write), run "Layout Upstream", then "Compact Layout Upstream", then "Loose Layout Upstream". Observe vertical spacing in the DAG.
**Expected:** Compact produces visibly tighter vertical gaps; Loose produces visibly wider vertical gaps; Normal is between them. Horizontal spacing between side inputs is identical across all three schemes.
**Why human:** Visual DAG inspection and running Nuke instance required.

#### 2. Shrink/Expand Selected correctness with mixed node types

**Test:** After running "Layout Upstream" on a graph that includes Dot nodes (e.g. a Merge with a masked input), select all nodes, run "Shrink Selected", then "Expand Selected".
**Expected:** Dot nodes move proportionally to regular nodes — no visual drift or disproportionate shift.
**Why human:** The center-based offset fix for Dots requires visual verification of the result in a live session.

#### 3. Shrink/Expand undo behavior

**Test:** Select 3+ nodes, run "Shrink Selected", confirm nodes move closer to anchor. Press Ctrl+Z. Confirm all nodes return to original positions in a single undo step.
**Expected:** Full undo in one keystroke, complete position restoration.
**Why human:** Nuke undo stack behavior requires a live session to verify.

---

### Gaps Summary

No gaps. All three success criteria are verified against the actual codebase. All 121 tests pass (23 more than the 98 counted in the initial verification, from the new `TestHorizontalOnlyScheme` class added by plan 05-03). The implementation is substantive, wired, and exercised by a comprehensive test suite.

---

_Verified: 2026-03-05T06:02:13Z_
_Verifier: Claude (gsd-verifier)_
