---
phase: 07-per-node-state-storage
verified: 2026-03-10T10:37:27Z
status: passed
score: 14/14 must-haves verified
re_verification: false
---

# Phase 7: Per-Node State Storage Verification Report

**Phase Goal:** Persist layout decisions per-node so that scheme, mode, and scale are stored on each node as a knob and can be replayed or cleared.
**Verified:** 2026-03-10T10:37:27Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | `node_layout_state.py` exists with all 5 functions exported | VERIFIED | File exists at `/workspace/node_layout_state.py`; all 5 functions present |
| 2  | `read_node_state()` returns defaults when knob absent, empty, or malformed | VERIFIED | Tests `test_returns_defaults_when_knob_absent`, `test_returns_defaults_when_knob_empty`, `test_returns_defaults_on_malformed_json` — all green |
| 3  | `write_node_state()` creates tab + state knob if absent; no duplicates on re-call | VERIFIED | Tests `test_creates_tab_and_state_knob_when_absent`, `test_does_not_duplicate_knobs_on_second_call` — both green |
| 4  | `clear_node_state()` removes state knob; only removes tab when `node_layout_diamond_dot` is also absent | VERIFIED | Tests `test_removes_state_knob`, `test_removes_tab_when_diamond_dot_absent`, `test_preserves_tab_when_diamond_dot_present` — all green |
| 5  | Scale accumulation: two 0.8 shrink calls store 0.64 with no float drift | VERIFIED | Tests `test_scale_accumulates_without_drift`, `test_two_shrink_sequence_stores_correct_value` — both green |
| 6  | `node_layout.py` write-back after `place_subtree()` in `layout_upstream()` | VERIFIED | AST test `test_state_write_after_place_subtree_in_layout_upstream` green; confirmed at line 619 (place_subtree) → line 625 (write-back loop) |
| 7  | `node_layout.py` write-back after `place_subtree()` in `layout_selected()` | VERIFIED | AST test `test_state_write_after_place_subtree_in_layout_selected` green; confirmed at line 714 (place_subtree) → line 717 (write-back loop) |
| 8  | `compute_dims()` memo key is `(id(node), scheme_multiplier)` tuple | VERIFIED | AST test `test_compute_dims_memo_key_is_tuple` green; confirmed at lines 286–287, 332 |
| 9  | `layout_upstream()` reads per-node stored scheme when `scheme_multiplier=None` | VERIFIED | AST test `test_layout_upstream_reads_per_node_state_when_scheme_is_none` green; `per_node_scheme` dict built at lines 600–614 using `read_node_state` |
| 10 | `_scale_selected_nodes()` writes accumulated h_scale/v_scale after scaling | VERIFIED | AST test `test_scale_selected_writes_state_after_scaling` green; write-back at lines 796–801 |
| 11 | `_scale_upstream_nodes()` writes accumulated h_scale/v_scale after scaling | VERIFIED | AST test `test_scale_upstream_writes_state_after_scaling` green; write-back at lines 820–825 |
| 12 | `clear_layout_state_selected()` and `clear_layout_state_upstream()` exist in `node_layout.py` | VERIFIED | Both functions present at lines 888 and 909; wrapped in undo groups; call `clear_node_state` per node |
| 13 | Both clear commands registered in `menu.py` | VERIFIED | Lines 27–28 of `menu.py`: `addCommand('Clear Layout State Selected', ...)` and `addCommand('Clear Layout State Upstream', ...)` |
| 14 | State knob uses `INVISIBLE` flag (not `DO_NOT_WRITE`) so it persists in `.nk` | VERIFIED | `node_layout_state.py` line 69: `state_knob.setFlag(nuke.INVISIBLE)`; no `DO_NOT_WRITE` found; test `test_sets_invisible_flag_on_state_knob` green |

**Score:** 14/14 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `node_layout_state.py` | Pure-Python state helpers; no top-level nuke import; 5 exported functions | VERIFIED | 113 lines; `import nuke` deferred inside `write_node_state`/`clear_node_state` only; all 5 functions present |
| `tests/test_node_layout_state.py` | 19 unit tests using FakeNode/FakeKnob Nuke stub | VERIFIED | 19 tests, all green; covers all read/write/clear/scheme/scale behaviors |
| `tests/test_state_integration.py` | 6 AST structural tests for integration points | VERIFIED | All 6 tests green (Plans 02–04 implementations complete) |
| `node_layout.py` | State write-back in `layout_upstream()`, `layout_selected()`, `_scale_selected_nodes()`, `_scale_upstream_nodes()`; per-node scheme resolution; clear functions | VERIFIED | All integration points present and wired |
| `menu.py` | Two new `addCommand` registrations for clear-state commands | VERIFIED | Lines 27–28; `menu.py` passes syntax check |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `node_layout.py` top-level | `node_layout_state` | `import node_layout_state` at line 4 | WIRED | Import confirmed |
| `layout_upstream()` | `node_layout_state.write_node_state()` | Write-back loop after `place_subtree()`, line 625–635 | WIRED | AST test green |
| `layout_selected()` | `node_layout_state.write_node_state()` | Write-back loop after `for root in roots:`, line 721–730 | WIRED | AST test green |
| `layout_upstream()` | `node_layout_state.read_node_state()` | `per_node_scheme` dict built at lines 607–610 | WIRED | AST test green |
| `compute_dims()` | memo dict | Key `(id(node), scheme_multiplier)` at lines 286–287, 332 | WIRED | AST test green |
| `_scale_selected_nodes()` | `node_layout_state.write_node_state()` | Write-back loop at lines 797–801 | WIRED | AST test green |
| `_scale_upstream_nodes()` | `node_layout_state.write_node_state()` | Write-back loop at lines 821–825 | WIRED | AST test green |
| `clear_layout_state_selected()` | `node_layout_state.clear_node_state()` | Iteration over `selectedNodes()`, line 901 | WIRED | Code confirmed |
| `clear_layout_state_upstream()` | `node_layout_state.clear_node_state()` | Iteration over `collect_subtree_nodes()`, line 920 | WIRED | Code confirmed |
| `menu.py` | `node_layout.clear_layout_state_selected` | `addCommand` at line 27 | WIRED | Confirmed |
| `menu.py` | `node_layout.clear_layout_state_upstream` | `addCommand` at line 28 | WIRED | Confirmed |

---

## Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| STATE-01 | 07-01, 07-02, 07-05 | Every node touched by a layout operation receives a hidden tab with knobs storing layout mode, scheme, and scale factor | SATISFIED | `write_node_state()` called in both `layout_upstream()` and `layout_selected()` write-back passes; knob creation guarded to prevent duplicates; INVISIBLE flag set |
| STATE-02 | 07-01, 07-02 | Hidden state knobs persist across .nk script save/close/reopen cycles | SATISFIED | `nuke.INVISIBLE` used (not `DO_NOT_WRITE`); INVISIBLE-flagged knobs are serialized into `.nk` by Nuke; `test_sets_invisible_flag_on_state_knob` green |
| STATE-03 | 07-03, 07-05 | Re-running a layout command replays stored scheme unless command explicitly specifies one | SATISFIED | `per_node_scheme` dict branches on `scheme_multiplier is not None`; None path calls `read_node_state()` per node; AST test green; clear commands allow reset so next layout starts fresh |
| STATE-04 | 07-04 | Shrink/Expand commands update the scale factor knob on affected nodes | SATISFIED | `_scale_selected_nodes()` and `_scale_upstream_nodes()` both accumulate `h_scale`/`v_scale` using `round(old * factor, 10)`; all 4 AST scale tests green |

**Orphaned requirements:** None — all 4 requirement IDs from REQUIREMENTS.md for Phase 7 are claimed across the 5 plans and verified.

---

## Anti-Patterns Found

None. Scanned `node_layout_state.py`, `node_layout.py`, `tests/test_node_layout_state.py`, and `tests/test_state_integration.py` for TODO/FIXME/PLACEHOLDER/HACK/XXX and empty implementations. Zero hits.

---

## Human Verification Required

### 1. State persists across Nuke script save/reopen (STATE-02)

**Test:** Open Nuke, run Layout Upstream on a small graph, save the script (.nk), close Nuke, reopen the script, inspect a node's knobs — verify the `node_layout_tab` tab and `node_layout_state` string knob are present with the expected JSON value.
**Expected:** Tab and knob survive the save/reopen cycle; JSON value contains scheme, mode, h_scale, v_scale.
**Why human:** The INVISIBLE flag behavior (persists to .nk) cannot be verified without a live Nuke runtime. The unit tests confirm the flag is set; only a live session can confirm the file I/O behavior.

### 2. Clear commands appear in Nuke layout menu

**Test:** Open Nuke, navigate to the Node Layout toolbar/menu, verify "Clear Layout State Selected" and "Clear Layout State Upstream" are visible as clickable entries.
**Expected:** Both menu items appear. Clicking them on selected nodes removes the state knob (verifiable via node property panel).
**Why human:** Menu rendering and toolbar visibility requires a live Nuke session; `menu.py` syntax and `addCommand` calls are verified programmatically but actual UI appearance is not.

### 3. Scheme replay behavior end-to-end

**Test:** Run Layout Upstream Compact on a graph (stores "compact" on all nodes). Then run Layout Upstream (no argument). Verify nodes are laid out using compact spacing without specifying it.
**Expected:** The no-argument Layout Upstream replays compact scheme from stored state.
**Why human:** Requires a live Nuke session to observe actual node spacing; the per-node scheme resolution code path is AST-verified but behavioral correctness of the replay needs visual/runtime confirmation.

---

## Test Suite Summary

```
Ran 193 tests in 0.885s
OK
```

- **19** unit tests in `test_node_layout_state.py` — all green
- **6** AST integration tests in `test_state_integration.py` — all green (were RED scaffold until Plans 02–04 completed)
- **168** pre-existing tests — all green, no regressions

---

## Gaps Summary

No gaps. All 14 must-have truths verified. All 4 requirements satisfied. All key links wired. Full test suite green with 193 passing tests.

---

_Verified: 2026-03-10T10:37:27Z_
_Verifier: Claude (gsd-verifier)_
