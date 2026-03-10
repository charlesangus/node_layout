---
phase: 07-per-node-state-storage
verified: 2026-03-10T12:10:00Z
status: passed
score: 17/17 must-haves verified
re_verification:
  previous_status: passed
  previous_score: 14/14
  gaps_closed:
    - "After Shrink/Expand Upstream, the bottom-left upstream node does not move (Plan 06)"
    - "Other upstream nodes are repositioned relative to the bottom-left anchor (Plan 06)"
    - "_scale_upstream_nodes applies snap_min floor matching _scale_selected_nodes (Plan 06)"
    - "After Shrink/Expand stores h_scale/v_scale, subsequent Layout Upstream/Selected uses those values (Plan 07)"
    - "compute_dims and place_subtree accept h_scale/v_scale; memo key extended to four-element tuple (Plan 07)"
    - "layout_upstream and layout_selected read per_node_h_scale/per_node_v_scale from stored state (Plan 07)"
  gaps_remaining: []
  regressions: []
---

# Phase 7: Per-Node State Storage Verification Report (Re-Verification)

**Phase Goal:** Per-node state memory for least-surprise re-layout — every layout-touched node stores its scheme, mode, and scale so that re-running layout reproduces the same geometry.
**Verified:** 2026-03-10T12:10:00Z
**Status:** passed
**Re-verification:** Yes — after UAT gap closure (Plans 06 and 07)

---

## Context

The initial VERIFICATION.md (2026-03-10T10:37:27Z) reported status `passed` at 14/14 truths.
Subsequent UAT (07-UAT.md) revealed two major gaps in test 4 (scale accumulation):

1. **Anchor drift** — `_scale_upstream_nodes()` used `nuke.selectedNode()` as pivot instead of the bottom-left upstream node. Fixed in Plan 06.
2. **Scale not replayed** — `layout_upstream()` and `layout_selected()` read stored scheme but not h_scale/v_scale; `compute_dims()` and `place_subtree()` had no h_scale/v_scale parameters. Fixed in Plan 07.

This re-verification covers all 14 original truths (regression check) plus 3 new truths from the gap closures.

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | `node_layout_state.py` exists with all 5 functions exported | VERIFIED | File exists; all 5 functions present (unchanged from initial) |
| 2  | `read_node_state()` returns defaults when knob absent, empty, or malformed | VERIFIED | 3 unit tests green; unchanged |
| 3  | `write_node_state()` creates tab + state knob if absent; no duplicates on re-call | VERIFIED | 2 unit tests green; unchanged |
| 4  | `clear_node_state()` removes state knob; preserves tab when diamond_dot present | VERIFIED | 3 unit tests green; unchanged |
| 5  | Scale accumulation: two 0.8 shrink calls store 0.64 with no float drift | VERIFIED | Unit tests green; unchanged |
| 6  | `layout_upstream()` write-back after `place_subtree()` | VERIFIED | AST test green; lines 632-649 unchanged |
| 7  | `layout_selected()` write-back after `place_subtree()` | VERIFIED | AST test green; lines 736-744 unchanged |
| 8  | `compute_dims()` memo key is four-element tuple `(id(node), scheme_multiplier, h_scale, v_scale)` | VERIFIED | Lines 286-287, 335: key is `(id(node), scheme_multiplier, h_scale, v_scale)`; AST test `test_compute_dims_memo_key_includes_h_scale` green |
| 9  | `layout_upstream()` reads per-node stored scheme when `scheme_multiplier=None` | VERIFIED | Lines 604-620; AST test green; unchanged |
| 10 | `_scale_selected_nodes()` writes accumulated h_scale/v_scale after scaling | VERIFIED | AST test green; write-back at lines ~797-801 unchanged |
| 11 | `_scale_upstream_nodes()` writes accumulated h_scale/v_scale after scaling | VERIFIED | Lines 854-859; unchanged |
| 12 | `clear_layout_state_selected()` and `clear_layout_state_upstream()` exist | VERIFIED | Both functions present; unchanged |
| 13 | Both clear commands registered in `menu.py` | VERIFIED | Lines 27-28; unchanged |
| 14 | State knob uses `INVISIBLE` flag (not `DO_NOT_WRITE`) | VERIFIED | `node_layout_state.py` line 69; unchanged |
| 15 | `_scale_upstream_nodes()` uses `max(upstream_nodes, key=lambda n: (n.ypos(), -n.xpos()))` as anchor pivot | VERIFIED | Line 832 of `node_layout.py`; AST test `test_scale_upstream_uses_max_upstream_nodes_as_anchor` green |
| 16 | `_scale_upstream_nodes()` applies `snap_min = get_dag_snap_threshold() - 1` floor matching `_scale_selected_nodes()` | VERIFIED | Lines 833, 845-848 of `node_layout.py`; AST test `test_snap_min_floor_guard_in_scale_upstream` green |
| 17 | `layout_upstream()` and `layout_selected()` read `h_scale`/`v_scale` from per-node state and pass root values to `compute_dims()`/`place_subtree()` | VERIFIED | Lines 607-633 (`layout_upstream`) and 699-736 (`layout_selected`); `compute_dims`/`place_subtree` signatures include `h_scale=1.0, v_scale=1.0`; 9 new AST tests green |

**Score:** 17/17 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `node_layout_state.py` | 5 exported functions; INVISIBLE flag on state knob | VERIFIED | Unchanged from initial; 19 unit tests green |
| `tests/test_node_layout_state.py` | 19 unit tests | VERIFIED | All 19 green |
| `tests/test_state_integration.py` | 16 AST structural tests (was 6; +1 Plan 06 anchor test; +9 Plan 07 scale-param/wiring tests) | VERIFIED | All 16 green |
| `tests/test_scale_nodes.py` | Updated to reflect snap_min floor in `_scale_upstream_nodes` | VERIFIED | `test_snap_min_floor_guard_in_scale_upstream` green; `test_no_snap_min_in_scale_upstream` correctly replaced |
| `node_layout.py` | `compute_dims`/`place_subtree` with h_scale/v_scale params; both layout entry points reading per-node scale; `_scale_upstream_nodes` with correct anchor and snap_min floor | VERIFIED | All integration points present and wired; 203 tests pass |
| `menu.py` | Two `addCommand` registrations for clear-state commands | VERIFIED | Lines 27-28; unchanged |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `node_layout.py` | `node_layout_state` | `import node_layout_state` | WIRED | Unchanged |
| `layout_upstream()` | `compute_dims()` / `place_subtree()` | `h_scale=root_h_scale, v_scale=root_v_scale` kwargs at lines 630-633 | WIRED | Confirmed |
| `layout_selected()` | `compute_dims()` / `place_subtree()` | `h_scale=root_h_scale, v_scale=root_v_scale` kwargs at lines 724, 736 | WIRED | Confirmed |
| `layout_upstream()` per-node loop | `per_node_h_scale` / `per_node_v_scale` | `scale_state = node_layout_state.read_node_state(subtree_node)` at line 618 | WIRED | AST tests `test_layout_upstream_builds_per_node_h_scale`, `test_layout_upstream_builds_per_node_v_scale` green |
| `layout_selected()` per-node loop | `per_node_h_scale` / `per_node_v_scale` | `scale_state = node_layout_state.read_node_state(sel_node)` at line 710 | WIRED | AST tests `test_layout_selected_builds_per_node_h_scale`, `test_layout_selected_builds_per_node_v_scale` green |
| `compute_dims()` | 4-element memo key | `(id(node), scheme_multiplier, h_scale, v_scale)` at lines 286-287, 335 | WIRED | AST test `test_compute_dims_memo_key_includes_h_scale` green |
| `compute_dims()` margins | `h_scale` / `v_scale` | `int(_horizontal_margin(...) * h_scale)` and `int(_subtree_margin(...) * v_scale)` at lines 293-294 | WIRED | Confirmed |
| `compute_dims()` gaps | `v_scale` with snap floor | `max(snap_threshold - 1, int(raw_gap * v_scale))` at lines 304, 326 | WIRED | Confirmed |
| `_scale_upstream_nodes()` | bottom-left anchor | `max(upstream_nodes, key=lambda n: (n.ypos(), -n.xpos()))` at line 832 | WIRED | AST test `test_scale_upstream_uses_max_upstream_nodes_as_anchor` green |
| `_scale_upstream_nodes()` | snap_min floor | `snap_min = get_dag_snap_threshold() - 1` + guards at lines 833, 845-848 | WIRED | AST test `test_snap_min_floor_guard_in_scale_upstream` green |
| `layout_upstream()` write-back | `node_layout_state.write_node_state()` | Lines 639-649 | WIRED | Unchanged |
| `layout_selected()` write-back | `node_layout_state.write_node_state()` | Lines 739-748 | WIRED | Unchanged |
| `clear_layout_state_selected()` | `node_layout_state.clear_node_state()` | Iteration over `selectedNodes()` | WIRED | Unchanged |
| `clear_layout_state_upstream()` | `node_layout_state.clear_node_state()` | Iteration over `collect_subtree_nodes()` | WIRED | Unchanged |
| `menu.py` | `node_layout.clear_layout_state_selected` | `addCommand` at line 27 | WIRED | Unchanged |
| `menu.py` | `node_layout.clear_layout_state_upstream` | `addCommand` at line 28 | WIRED | Unchanged |

---

## Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| STATE-01 | 07-01, 07-02, 07-05 | Every node touched by a layout operation receives a hidden tab with knobs storing layout mode, scheme, and scale factor | SATISFIED | `write_node_state()` called in both layout entry-point write-back passes; INVISIBLE flag set; 19 unit tests green |
| STATE-02 | 07-01, 07-02 | Hidden state knobs persist across .nk script save/close/reopen cycles | SATISFIED | `nuke.INVISIBLE` (not `DO_NOT_WRITE`) confirmed at `node_layout_state.py` line 69; `test_sets_invisible_flag_on_state_knob` green; UAT test 2 passed in live session |
| STATE-03 | 07-03, 07-05, 07-07 | Re-running a layout command replays the stored scheme unless the command explicitly specifies one | SATISFIED | Per-node scheme resolution in `layout_upstream` (lines 604-624) and `layout_selected` (lines 696-721); h_scale/v_scale also replayed (Plan 07); UAT test 3 passed |
| STATE-04 | 07-04, 07-06, 07-07 | Shrink/Expand commands update the scale factor knob on affected nodes | SATISFIED | `_scale_selected_nodes` and `_scale_upstream_nodes` both write h_scale/v_scale; anchor pivot fixed (Plan 06); scale wired into re-layout (Plan 07); UAT test 4 gap closed |

**Orphaned requirements:** None — all 4 requirement IDs from REQUIREMENTS.md for Phase 7 are claimed across the 7 plans and verified.

---

## Anti-Patterns Found

None. Scanned `node_layout.py`, `node_layout_state.py`, `tests/test_state_integration.py`, and `tests/test_scale_nodes.py` for TODO/FIXME/PLACEHOLDER/HACK/XXX and empty implementations. Zero hits.

---

## Human Verification Required

### 1. Scale accumulation replay (UAT test 4 — re-test)

**Test:** Open Nuke, run Layout Upstream on a small graph. Run Shrink Selected once on a node. Check `node_layout_state` — h_scale and v_scale should be < 1.0. Run Layout Upstream again (no scheme argument). Verify the re-laid-out nodes use tighter spacing than the initial layout (matching the stored h_scale/v_scale from the Shrink).
**Expected:** Nodes are spaced more tightly after re-layout, proportional to stored h_scale/v_scale. Anchor node (bottom-left of upstream tree) does not move during Shrink/Expand Upstream.
**Why human:** Requires a live Nuke session to observe actual node spacing. The wiring from state into compute_dims/place_subtree is AST-verified but behavioral correctness of the spacing needs visual confirmation. The original UAT reported "subsequent layouts do not respect the setting" — this re-test confirms Plan 07 closes that gap.

### 2. State persists across Nuke script save/reopen (STATE-02 — confirmed in initial UAT)

**Test:** Open Nuke, run Layout Upstream on a small graph, save the .nk, close Nuke, reopen the script, inspect a node's knobs via Script Editor — `nuke.selectedNode()['node_layout_state'].value()` should return JSON with scheme, mode, h_scale, v_scale.
**Expected:** Tab and knob survive save/reopen cycle.
**Why human:** Requires live Nuke runtime. UAT test 2 already passed; this is a regression check note only.

### 3. Clear commands appear in Nuke layout menu (confirmed in initial UAT)

**Test:** Open Nuke, navigate to layout menu — verify "Clear Layout State Selected" and "Clear Layout State Upstream" are present.
**Expected:** Both items visible and functional. UAT tests 5, 6, 7 already passed.
**Why human:** Menu UI requires live Nuke session.

---

## Test Suite Summary

```
Ran 203 tests in 1.089s
OK
```

- **19** unit tests in `test_node_layout_state.py` — all green
- **16** AST integration tests in `test_state_integration.py` — all green (was 6; +1 Plan 06 anchor; +9 Plan 07 scale-param/wiring)
- **168** pre-existing tests across all other test files — all green, no regressions

**Tests added by gap-closure plans:**
- Plan 06: `TestUpstreamAnchorAST` (1 test) — confirms `max(upstream_nodes` as anchor
- Plan 07 Task 1: `TestScaleParamsAST` (3 tests) — confirms `h_scale=1.0` params in `compute_dims`/`place_subtree` and extended memo key
- Plan 07 Task 2: `TestScaleWiringAST` (6 tests) — confirms `per_node_h_scale`/`per_node_v_scale` and `root_h_scale`/`root_v_scale` in both layout entry points

---

## Gaps Summary

No gaps. All 17 must-have truths verified. All 4 requirements satisfied. All key links wired. Full test suite green with 203 passing tests.

The two UAT gaps (anchor drift in `_scale_upstream_nodes` and h_scale/v_scale not replayed on re-layout) are fully closed by Plans 06 and 07. No regressions introduced.

---

_Verified: 2026-03-10T12:10:00Z_
_Verifier: Claude (gsd-verifier)_
