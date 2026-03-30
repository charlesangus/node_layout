---
phase: 17-prefs-dialog-foundation
verified: 2026-03-30T00:00:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 17: Prefs Dialog Foundation Verification Report

**Phase Goal:** Lay the preference and dialog foundation that leader key features depend on
**Verified:** 2026-03-30
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `NodeLayoutPrefs` returns 0 for `hint_popup_delay_ms` on a clean install | VERIFIED | `DEFAULTS["hint_popup_delay_ms"] = 0` at line 19 of `node_layout_prefs.py`; `test_default_hint_popup_delay_ms` passes |
| 2 | The preferences dialog contains a Leader Key section with a Hint popup delay (ms) field | VERIFIED | `_make_section_header("Leader Key")` at line 85, `self.hint_popup_delay_ms_edit = QLineEdit()` at line 87 of `node_layout_prefs_dialog.py`; Leader Key section appears before Advanced section |
| 3 | Entering a value in the dialog and clicking OK persists to prefs file and is returned by NodeLayoutPrefs | VERIFIED | `_on_accept` parses `hint_popup_delay_ms_value`, calls `prefs_instance.set("hint_popup_delay_ms", hint_popup_delay_ms_value)` then `prefs_instance.save()`; `test_round_trip_hint_popup_delay_ms` passes |
| 4 | Entering a negative value is silently rejected (dialog stays open) | VERIFIED | Guard `if hint_popup_delay_ms_value < 0: return` at line 160 of `node_layout_prefs_dialog.py` |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `node_layout_prefs.py` | `hint_popup_delay_ms` default in DEFAULTS dict | VERIFIED | Line 19: `"hint_popup_delay_ms": 0` with comment; 12 total DEFAULTS keys |
| `node_layout_prefs_dialog.py` | Leader Key section with `hint_popup_delay_ms` field | VERIFIED | Section header at line 85, QLineEdit at line 87, populate at line 127-129, parse+guard+set at lines 144/160/175 |
| `tests/test_node_layout_prefs.py` | Tests for `hint_popup_delay_ms` default and round-trip | VERIFIED | `test_default_hint_popup_delay_ms`, `test_defaults_contains_all_twelve_keys`, `test_round_trip_hint_popup_delay_ms`, fallback assertion in `test_missing_keys_fall_back_to_defaults` |
| `tests/test_node_layout_prefs_dialog.py` | AST tests for Leader Key section in dialog | VERIFIED | `TestDialogLeaderKeySection` class with 5 structural tests |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `node_layout_prefs_dialog.py` | `node_layout_prefs.py` | `prefs_instance.get/set("hint_popup_delay_ms")` | WIRED | `prefs_instance.get("hint_popup_delay_ms")` at line 128; `prefs_instance.set("hint_popup_delay_ms", hint_popup_delay_ms_value)` at line 175 |

### Data-Flow Trace (Level 4)

The dialog is a form editor backed by the JSON prefs file — no dynamic render pass to trace. The data flow is:

1. `_populate_from_prefs` reads `prefs_singleton.get("hint_popup_delay_ms")` and sets `hint_popup_delay_ms_edit` text — read path is live.
2. `_on_accept` parses the edit field, validates, calls `prefs_instance.set(...)` then `prefs_instance.save()` — write path is live.
3. Round-trip test `test_round_trip_hint_popup_delay_ms` confirms set+save+new-instance+get returns 500 (not default).

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `node_layout_prefs_dialog.py` | `hint_popup_delay_ms_edit` text | `prefs_singleton` JSON file | Yes — `json.dump`/`json.load` cycle confirmed by round-trip test | FLOWING |

### Behavioral Spot-Checks

The dialog requires a display server (PySide6 `QDialog`) and cannot be instantiated headlessly. The AST-based tests in `test_node_layout_prefs_dialog.py` cover all structural behaviors without running Qt. The prefs module is pure Python and fully testable.

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `hint_popup_delay_ms` default = 0 | `python3 -m pytest tests/test_node_layout_prefs.py -q` | 22 passed | PASS |
| Round-trip persistence | `python3 -m pytest tests/test_node_layout_prefs.py::TestNewPrefsRoundTrip::test_round_trip_hint_popup_delay_ms -v` | PASSED | PASS |
| Dialog Leader Key section structure | `python3 -m pytest tests/test_node_layout_prefs_dialog.py::TestDialogLeaderKeySection -v` | 5 passed | PASS |
| Full suite (prefs + dialog + integration) | `python3 -m pytest tests/test_node_layout_prefs.py tests/test_node_layout_prefs_dialog.py tests/test_prefs_integration.py -q` | 84 passed | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PREF-01 | 17-01-PLAN.md | A "hint popup delay (ms)" preference is added with default 0 | SATISFIED | `DEFAULTS["hint_popup_delay_ms"] = 0` in `node_layout_prefs.py` line 19 |
| PREF-02 | 17-01-PLAN.md | The hint popup delay preference is exposed in the preferences dialog | SATISFIED | Leader Key section with `hint_popup_delay_ms_edit` QLineEdit in `node_layout_prefs_dialog.py` lines 83-88 |

No orphaned requirements — REQUIREMENTS.md traceability table maps only PREF-01 and PREF-02 to Phase 17, and both are claimed by 17-01-PLAN.md.

### Anti-Patterns Found

None. No TODO/FIXME/placeholder comments, empty returns, or stub patterns found in the four modified files. The SUMMARY notes that `hint_popup_delay_ms` runtime consumption is deferred to Phase 18 by design — this is an intentional phasing decision, not a stub.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | — |

### Human Verification Required

1. **Dialog visual appearance**
   **Test:** Open the preferences dialog in a live Nuke session. Verify the "Leader Key" section header appears bold between "Scheme Multipliers" and "Advanced" sections, and that "Hint popup delay (ms)" label and text field render correctly.
   **Expected:** Bold "Leader Key" header, a single QLineEdit showing "0" by default, positioned above the "Advanced" section.
   **Why human:** Qt widget rendering requires a display server and live Nuke environment; not testable in CI.

2. **Negative value rejection in dialog**
   **Test:** Open the dialog, enter -1 in "Hint popup delay (ms)", click OK.
   **Expected:** Dialog remains open (silent rejection); prefs file is not updated.
   **Why human:** The `_on_accept` guard logic (`if hint_popup_delay_ms_value < 0: return`) is verified structurally, but actual Qt dialog close behavior requires a live session.

### Gaps Summary

No gaps. All four must-have truths are verified, all four artifacts are substantive and wired, the key link from dialog to prefs singleton is confirmed at both read and write paths, and both PREF-01 and PREF-02 requirements are satisfied. The full test suite (84 tests) passes with 0 failures. Two items are flagged for human verification due to Qt rendering requirements, but these do not block goal achievement.

---

_Verified: 2026-03-30_
_Verifier: Claude (gsd-verifier)_
