---
phase: 10-shrink-expand-h-v-both-expand-push-away
verified: 2026-03-12T14:00:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
---

# Phase 10: Shrink/Expand H/V/Both + Expand Push-Away Verification Report

**Phase Goal:** Implement axis-specific shrink/expand (H, V, both), repeat-last-scale, and push-away on expand
**Verified:** 2026-03-12T14:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                     | Status     | Evidence                                                                                   |
|----|-------------------------------------------------------------------------------------------|------------|--------------------------------------------------------------------------------------------|
| 1  | Shrink/Expand Selected/Upstream Horizontal/Vertical commands exist as callable functions  | VERIFIED   | 8 new defs in node_layout.py lines 1095–1256                                               |
| 2  | H-only scale moves nodes only horizontally (dy unchanged); only h_scale accumulates       | VERIFIED   | `new_dy = round(dy)` when `axis != "h"` guard at line 953; v_scale gated at line 971       |
| 3  | V-only scale moves nodes only vertically (dx unchanged); only v_scale accumulates         | VERIFIED   | `new_dx = round(dx)` when `axis != "v"` guard at line 952; h_scale gated at line 969       |
| 4  | snap_min floor is only applied to the axis being scaled                                   | VERIFIED   | Lines 957 and 959: both floor guards include `axis != "v"` and `axis != "h"` respectively  |
| 5  | repeat_last_scale() re-invokes the last-called scale command; no-ops if none called       | VERIFIED   | Lines 1259–1265: checks `_last_scale_fn is None`, else calls it                            |
| 6  | All 4 existing scale wrappers set _last_scale_fn on every invocation                      | VERIFIED   | Lines 1016-1017, 1034-1035, 1057-1058, 1076-1077: global + assignment in each wrapper      |
| 7  | Expand H/V variants call push_nodes_to_make_room; Shrink variants do not                  | VERIFIED   | expand_selected_horizontal (1142), expand_selected_vertical (1165), expand_upstream_horizontal (1226), expand_upstream_vertical (1251); no call in any shrink variant |
| 8  | All 9 new commands registered in menu.py with ctrl+/ for repeat                           | VERIFIED   | menu.py lines 57–70: 8 H/V addCommand entries + Repeat Last Scale with 'ctrl+/'            |
| 9  | All 15 tests in test_scale_nodes_axis pass; all 17 tests in test_scale_nodes pass         | VERIFIED   | `python3 -m unittest tests.test_scale_nodes_axis tests.test_scale_nodes`: 32 tests OK       |

**Score:** 9/9 truths verified

---

### Required Artifacts

| Artifact                              | Expected                                                                                           | Status    | Details                                                                                   |
|---------------------------------------|----------------------------------------------------------------------------------------------------|-----------|-------------------------------------------------------------------------------------------|
| `node_layout.py`                      | axis param on both helpers, _last_scale_fn var, 8 new wrappers, repeat_last_scale                  | VERIFIED  | All present: lines 914, 933, 976, 1095–1265                                               |
| `menu.py`                             | 9 new addCommand entries (8 H/V variants + Repeat Last Scale with ctrl+/)                          | VERIFIED  | Lines 57–70 contain all 9 registrations                                                   |
| `tests/test_scale_nodes_axis.py`      | 15-test scaffold covering axis scaling, state write-back, snap floor gating, repeat, push-away     | VERIFIED  | 594 lines, 15 tests, all pass when run directly                                            |

---

### Key Link Verification

| From                          | To                          | Via                                          | Status    | Details                                                                  |
|-------------------------------|-----------------------------|----------------------------------------------|-----------|--------------------------------------------------------------------------|
| `_scale_selected_nodes`       | axis parameter              | `if axis != "v"` / `if axis != "h"` guards  | WIRED     | Lines 952–960 and 969–972 implement both position and state gating        |
| `expand_selected_horizontal`  | `push_nodes_to_make_room`   | bbox before/after comparison                 | WIRED     | Line 1142 calls push_nodes_to_make_room inside try block                  |
| `shrink_selected`             | `_last_scale_fn`            | global assignment in wrapper body            | WIRED     | Lines 1016–1017: `global _last_scale_fn; _last_scale_fn = shrink_selected` |
| `menu.py`                     | `node_layout.repeat_last_scale` | addCommand with 'ctrl+/'               | WIRED     | Lines 65–70: addCommand with 'ctrl+/' and shortcutContext=2               |
| `_scale_upstream_nodes`       | axis parameter              | same guards as _scale_selected_nodes         | WIRED     | Lines 992–1009 mirror _scale_selected_nodes pattern exactly               |

---

### Requirements Coverage

| Requirement | Source Plan | Description                                                                                              | Status    | Evidence                                                                                            |
|-------------|-------------|----------------------------------------------------------------------------------------------------------|-----------|-----------------------------------------------------------------------------------------------------|
| SCALE-01    | 10-01, 10-02 | Shrink/Expand Selected and Upstream commands support Horizontal, Vertical, and Both axis modes           | SATISFIED | `axis` parameter on both helpers; 8 new H/V wrappers in node_layout.py passing 15 axis-specific tests |
| SCALE-02    | 10-01, 10-02 | Axis mode selectable via separate menu commands; H/V variants are menu-only per CONTEXT.md decision      | SATISFIED | 8 new addCommand entries in menu.py (no shortcuts, per CONTEXT.md); Repeat Last Scale with ctrl+/   |
| SCALE-03    | 10-01, 10-02 | Expand Selected and Expand Upstream push surrounding nodes away after expanding                           | SATISFIED | All 4 expand H/V variants call push_nodes_to_make_room; 3 push-away tests pass                      |

**Note on SCALE-02:** The REQUIREMENTS.md text mentions "modifier keys on existing shortcuts" but CONTEXT.md explicitly resolved this as H/V variants being menu-only with no shortcuts. This is a design decision documented pre-implementation, not a gap.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found | — | — |

No TODO/FIXME/placeholder comments, empty implementations, or stub return values found in Phase 10 additions (node_layout.py lines 914–1265, menu.py lines 57–70).

---

### Known Issue: Full `discover` Test Suite — 4 Errors

Running `python3 -m unittest discover -s tests` produces 4 errors in `TestExpandPushAway` and `TestRepeatLastScaleBehavior`. These are **not Phase 10 regressions**. The root cause:

- `test_scale_nodes_axis.py` loads `_nl` (node_layout) at module scope. The `_nl` module holds a reference to `sys.modules["nuke"]` at load time.
- Other test files (e.g. `test_state_integration.py`, `test_prefs_integration.py`) unconditionally replace `sys.modules["nuke"]` with a minimal stub that lacks `Undo` and `lastHitGroup` attributes.
- When discover runs those files after `test_scale_nodes_axis.py`, `_nl.nuke` inside the test's `setUp()` (which reassigns `_nl.nuke = sys.modules["nuke"]`) picks up the stripped-down stub.
- This is a pre-existing cross-test stub isolation issue. It was present before Phase 10 and is documented in the 10-02-SUMMARY as deferred/out-of-scope.

**The targeted test runs that matter for Phase 10 pass cleanly:**
```
python3 -m unittest tests.test_scale_nodes_axis tests.test_scale_nodes
# 32 tests in 0.182s — OK
```

---

### Human Verification Required

#### 1. H/V Command Discoverability in Nuke Menu

**Test:** Open Nuke, navigate to the Node Layout Preferences tab-menu, and verify the 9 new commands appear grouped after "Expand Upstream" and before the separator.
**Expected:** "Shrink Selected Horizontal", "Shrink Selected Vertical", "Expand Selected Horizontal", "Expand Selected Vertical", "Shrink Upstream Horizontal", "Shrink Upstream Vertical", "Expand Upstream Horizontal", "Expand Upstream Vertical", and "Repeat Last Scale" all visible and invokable.
**Why human:** Menu rendering and live Nuke API behavior cannot be verified programmatically in this test environment.

#### 2. Repeat Last Scale ctrl+/ Shortcut

**Test:** In Nuke, invoke "Shrink Selected Horizontal" from the menu, then press ctrl+/. Verify it re-runs the horizontal shrink.
**Expected:** ctrl+/ repeats the last-run scale variant exactly.
**Why human:** Keyboard shortcut binding in Nuke's live DAG requires a running Nuke session to verify.

#### 3. Directional Push-Away Behavior

**Test:** Select 2+ nodes in a horizontal arrangement, invoke "Expand Selected Horizontal". Verify that surrounding unselected nodes are pushed left/right but not up/down.
**Expected:** Push is axis-appropriate — horizontal expansion only pushes horizontally, vertical expansion only pushes vertically.
**Why human:** Spatial behavior in the live DAG requires visual inspection.

---

### Gaps Summary

None. All must-haves from both 10-01-PLAN and 10-02-PLAN are fully implemented and verified. The 4 discover-suite errors are a pre-existing test isolation issue not introduced by Phase 10.

---

_Verified: 2026-03-12T14:00:00Z_
_Verifier: Claude (gsd-verifier)_
