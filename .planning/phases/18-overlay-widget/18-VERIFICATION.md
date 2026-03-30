---
phase: 18-overlay-widget
verified: 2026-03-30T00:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 18: Overlay Widget Verification Report

**Phase Goal:** Build the LeaderKeyOverlay floating HUD widget (node_layout_overlay.py) and its structural test suite.
**Verified:** 2026-03-30
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                     | Status     | Evidence                                                                                      |
|----|-------------------------------------------------------------------------------------------|------------|-----------------------------------------------------------------------------------------------|
| 1  | LeaderKeyOverlay widget can be shown over a parent without stealing keyboard focus        | VERIFIED  | `WA_ShowWithoutActivating` set in `__init__` (line 62); `Qt.WindowType.Tool` set (line 61)   |
| 2  | All 10 active command keys are displayed in QWERTY grid positions with their action labels | VERIFIED  | `_KEY_LAYOUT` list confirmed correct by AST extraction; grid positions match D-05 exactly     |
| 3  | Chaining keys (WASD/QE) use a visually distinct badge color from single-shot keys (VZFC)  | VERIFIED  | `_CHAINING_KEY_COLOR` and `_SINGLE_SHOT_KEY_COLOR` are distinct module-level constants; `CHAINING_KEYS = {"W","A","S","D","Q","E"}` drives per-cell selection in `_make_key_cell` |
| 4  | The overlay centers itself over its parent widget on each show() call                     | VERIFIED  | `show()` calls `super().show()` then `self.move(global_center - self.rect().center())` (lines 153-163) |
| 5  | hide() fully dismisses the overlay with no residual widget on screen                     | VERIFIED  | `hide()` is inherited unmodified from QWidget — Qt standard behavior; D-14 decision locks this as the intended approach; no override that could break dismissal exists |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact                              | Expected                                | Level 1: Exists | Level 2: Substantive | Level 3: Wired     | Status   |
|---------------------------------------|-----------------------------------------|-----------------|----------------------|--------------------|----------|
| `node_layout_overlay.py`              | LeaderKeyOverlay QWidget class          | YES (164 lines) | YES — full class with `__init__`, `_build_ui`, `_make_key_cell`, `paintEvent`, `show` | YES — `class LeaderKeyOverlay(QWidget)` | VERIFIED |
| `tests/test_node_layout_overlay.py`   | AST/structural tests for overlay widget | YES (307 lines) | YES — 6 test classes, 19 test methods, stdlib-only | YES — loads `node_layout_overlay.py` via `OVERLAY_PATH` path | VERIFIED |

---

### Key Link Verification

| From                        | To                                        | Via                          | Pattern                                      | Status   | Details                                    |
|-----------------------------|-------------------------------------------|------------------------------|----------------------------------------------|----------|--------------------------------------------|
| `node_layout_overlay.py`    | `PySide6.QtWidgets.QWidget`               | class inheritance            | `class LeaderKeyOverlay(QWidget)`            | WIRED   | Confirmed at line 45                        |
| `node_layout_overlay.py`    | `Qt.WidgetAttribute.WA_ShowWithoutActivating` | setAttribute call in __init__ | `WA_ShowWithoutActivating`                   | WIRED   | Confirmed at line 62                        |
| `tests/test_node_layout_overlay.py` | `node_layout_overlay.py`       | AST source loading           | `node_layout_overlay\.py`                   | WIRED   | `OVERLAY_PATH` set at line 22; all 19 tests load source via `_load_overlay_source()` |

---

### Data-Flow Trace (Level 4)

Not applicable. This phase produces a PySide6 widget (visual component) rather than a data-rendering pipeline. The overlay displays static key-label data defined at module level in `_KEY_LAYOUT` — there is no dynamic data source to trace. The widget is a pure UI primitive; data flow is deliberately deferred to Phase 19 (event filter wires show/hide calls).

---

### Behavioral Spot-Checks

| Behavior                                  | Command                                   | Result          | Status  |
|-------------------------------------------|-------------------------------------------|-----------------|---------|
| All 19 overlay structural tests pass      | `python3 -m pytest tests/test_node_layout_overlay.py -v` | 19/19 passed (0.03s) | PASS   |
| No regressions in full test suite         | `python3 -m pytest tests/ --ignore=tests/test_freeze_integration.py -q` | 366 passed (4.85s) | PASS  |
| Module parses cleanly as valid Python AST | `ast.parse(open('node_layout_overlay.py').read())` | OK — single class `LeaderKeyOverlay` | PASS |
| Test file has no PySide6 imports          | String search for `PySide6` in test file  | Not present    | PASS   |
| CHAINING_KEYS contains exactly W,A,S,D,Q,E | AST extraction of set members            | `{'A','D','E','Q','S','W'}` — exact match | PASS |
| _KEY_LAYOUT grid positions match D-05     | AST extraction of 10 tuples              | Q(0,0) W(0,1) E(0,2) A(1,0) S(1,1) D(1,2) F(1,3) Z(2,0) C(2,2) V(2,3) — exact match | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description                                                                           | Status    | Evidence                                                                              |
|-------------|-------------|---------------------------------------------------------------------------------------|-----------|---------------------------------------------------------------------------------------|
| OVRL-01     | 18-01-PLAN  | An icon-style keyboard overlay is displayed over the active DAG on leader arm, after the hint popup delay | SATISFIED (widget) | `LeaderKeyOverlay` widget exists and is visually complete; "after hint popup delay" is a runtime orchestration concern deferred to Phase 19 by plan design |
| OVRL-02     | 18-01-PLAN  | The overlay shows only the active command keys with their action labels               | SATISFIED | All 10 keys in `_KEY_LAYOUT` with correct action labels; `QGridLayout` places them in QWERTY positions |
| OVRL-03     | 18-01-PLAN  | The overlay does not steal keyboard focus from the DAG                                | SATISFIED | `WA_ShowWithoutActivating` + `Qt.WindowType.Tool` both set in `__init__` before any `show()` call |
| OVRL-04     | 18-01-PLAN  | The overlay is dismissed when leader mode exits                                       | SATISFIED (widget) | `hide()` inherited from QWidget is the dismissal mechanism; actual "leader mode exit" trigger is Phase 19's responsibility (stated explicitly in CONTEXT.md and PLAN docstring) |

No orphaned requirements. All four OVRL IDs appear in the plan's `requirements` field and are accounted for.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | — |

No TODO/FIXME/PLACEHOLDER comments found. No stub return values (empty list/dict/null). No console.log-only handlers. No hardcoded empty props. The implementation is complete for its stated phase scope.

---

### Human Verification Required

#### 1. Visual appearance of the floating HUD

**Test:** In a live Nuke session (with Phase 19 wired), trigger leader mode and observe the overlay.
**Expected:** Dark semi-transparent rounded panel floating over the DAG; "LEADER KEY" title at top; 10 key badges in QWERTY grid positions; WASD/QE badges in teal/blue, VZFC badges in neutral white/gray; action label in small gray text below each badge.
**Why human:** Visual appearance (opacity, color rendering, font rendering, rounded corners) cannot be verified without a display server and a live Qt widget instance.

#### 2. Focus non-stealing behavior

**Test:** In a live Nuke session, activate the leader key overlay and type a key.
**Expected:** The overlay appears but the DAG panel retains focus — keystrokes are processed by the DAG's event filter, not captured by the overlay.
**Why human:** Focus behavior depends on the OS window manager and Nuke's embedding hierarchy; `WA_ShowWithoutActivating` is the correct Qt attribute but its effect in a specific embedded hierarchy can only be confirmed by a human interaction test.

#### 3. Overlay centering on show()

**Test:** In a live Nuke session with a non-default Nuke window layout, trigger the overlay.
**Expected:** The overlay appears centered over the active DAG panel, not at a screen corner or fixed position.
**Why human:** `mapToGlobal()` centering math requires a real native window and non-zero parent geometry to verify.

#### 4. hide() leaves no residual widget

**Test:** Show the overlay, then dismiss leader mode (Phase 19 calls `hide()`).
**Expected:** The overlay fully disappears with no ghost/residual widget on screen.
**Why human:** Qt widget visibility state after `hide()` can only be confirmed visually in a live session.

---

### Gaps Summary

No gaps. All must-haves are verified at all three levels. All four requirement IDs (OVRL-01 through OVRL-04) are satisfied by the implementation within the stated phase scope. The structural test suite runs entirely without a display server (19/19 pass), and the full suite shows no regressions (366/366 pass).

The two items appropriately deferred to Phase 19 — (a) "after hint popup delay" timing in OVRL-01 and (b) leader mode exit triggering hide() in OVRL-04 — are correctly scoped out of this phase by the plan and CONTEXT.md. They are not gaps in Phase 18; they are Phase 19 inputs.

---

_Verified: 2026-03-30_
_Verifier: Claude (gsd-verifier)_
