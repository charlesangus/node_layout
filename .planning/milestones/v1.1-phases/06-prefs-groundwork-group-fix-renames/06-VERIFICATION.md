---
phase: 06-prefs-groundwork-group-fix-renames
verified: 2026-03-09T00:00:00Z
status: passed
score: 14/14 must-haves verified
re_verification:
  previous_status: passed
  previous_score: 13/13
  gaps_closed:
    - "UAT.md updated to status: complete with passed: 6, issues: 0 — Group View test confirmed passing by user in live Nuke session (Plan 06-05)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Open prefs dialog in Nuke and inspect section headers"
    expected: "Three bold section labels visible — Spacing, Scheme Multipliers, Advanced — with no box borders around sections"
    why_human: "PySide6 rendering of bold QLabel fonts requires a display server and live Nuke session"
  - test: "Run Layout Upstream inside a Group opened via Ctrl-Enter"
    expected: "Dot nodes created by layout appear inside the Group, not at root level"
    why_human: "Requires a live Nuke session with an active Group context"
  - test: "Run Layout Upstream inside a Group opened via Group View panel"
    expected: "Dot nodes created by layout appear inside the Group, not at root level — this is the scenario fixed by Plan 06-04 and confirmed via UAT re-run"
    why_human: "Requires a live Nuke session with a Group View panel active; user confirmed pass during Plan 06-05 UAT re-run"
  - test: "Run layout command that triggers push-away inside a Group"
    expected: "Only nodes inside the Group are pushed; root-level nodes do not move"
    why_human: "Requires a live Nuke session with both Group context and root-level nodes present simultaneously"
---

# Phase 6: Prefs Groundwork, Group Fix & Renames — Verification Report

**Phase Goal:** Lay the groundwork for user-configurable layout preferences, fix Group context bugs, and rename menu commands to scheme names.
**Verified:** 2026-03-09T00:00:00Z
**Status:** PASSED
**Re-verification:** Yes — after Plan 06-05 UAT closure (all 6 UAT tests confirmed passing by user)

## Scope

This verification covers all five plans: 06-01 (prefs groundwork), 06-02 (H-axis decoupling), 06-03 (Group context wrapping), 06-04 (lastHitGroup gap closure), and 06-05 (UAT re-run closure).

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can open the prefs dialog and see a 'Horizontal Subtree Gap' field that persists when saved | VERIFIED | `horizontal_subtree_gap_edit` wired at dialog line 49; `set("horizontal_subtree_gap", ...)` at line 135 |
| 2 | User can open the prefs dialog and see a 'Horizontal Mask Gap' field that persists when saved | VERIFIED | `horizontal_mask_gap_edit` wired at dialog line 52; `set("horizontal_mask_gap", ...)` at line 136 |
| 3 | User can open the prefs dialog and see a 'Dot Font Reference Size' field that persists when saved | VERIFIED | `dot_font_reference_size_edit` at dialog line 81; `set("dot_font_reference_size", ...)` at line 143 |
| 4 | Dialog fields are organized into three visually distinct sections: Spacing, Scheme Multipliers, Advanced | VERIFIED | `_make_section_header("Spacing")` at line 47, `_make_section_header("Scheme Multipliers")` at line 63, `_make_section_header("Advanced")` at line 79 |
| 5 | Fresh prefs produce less-tall, wider layouts than v1.0 defaults | VERIFIED | `base_subtree_margin=200` (was 300), `loose_gap_multiplier=8.0` (was 12.0), `horizontal_subtree_gap=150` is new absolute H-axis control |
| 6 | Horizontal margins between subtrees are absolute pixel values from prefs, not sqrt-scaled by node count | VERIFIED | `_horizontal_margin()` at node_layout.py line 131 reads `horizontal_subtree_gap` or `horizontal_mask_gap` directly — no sqrt formula in function body |
| 7 | layout_selected() uses horizontal_subtree_gap directly for horizontal_clearance, no sqrt formula | VERIFIED | `horizontal_clearance = current_prefs.get("horizontal_subtree_gap")` at line 670 |
| 8 | All test files use /workspace paths and the full test suite passes | VERIFIED | 168 tests pass, 0 errors, 0 failures |
| 9 | layout_upstream() and layout_selected() capture nuke.lastHitGroup() as the very first Nuke API call before any other operation | VERIFIED | `current_group = nuke.lastHitGroup()` at lines 583 and 633; zero occurrences of `nuke.thisGroup()` in node_layout.py |
| 10 | All node-creation operations inside layout_upstream() and layout_selected() run inside 'with current_group:' | VERIFIED | `with current_group:` at line 589 (layout_upstream) and line 641 (layout_selected), wrapping entire try-body |
| 11 | push_nodes_to_make_room() uses group.nodes() scoped to current_group instead of nuke.allNodes() | VERIFIED | Signature at line 531; `current_group.nodes() if current_group is not None else nuke.allNodes()` at line 544 |
| 12 | Scheme commands in menu.py are named 'Layout Upstream Compact', 'Layout Selected Compact', 'Layout Upstream Loose', 'Layout Selected Loose' | VERIFIED | All 4 names confirmed in menu.py lines 23–26 with CMD-01 comment at line 22 |
| 13 | Dot nodes created by layout commands land inside the Group when the user is viewing it via Group View panel (not just Ctrl-Enter) | VERIFIED | `nuke.lastHitGroup()` is the canonical Nuke API for Group View panel context; AST tests assert `lastHitGroup()` at both entry points |
| 14 | UAT.md records all 6 UAT tests as passing with status: complete and issues: 0 | VERIFIED | UAT.md frontmatter: `status: complete`, `passed: 6`, `issues: 0`; gap entry `status: closed`, `closed_by: "06-04-PLAN.md"`, `verified_by: "UAT re-run — user confirmed pass"` |

**Score:** 14/14 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `node_layout_prefs.py` | DEFAULTS dict with 10 keys including horizontal_subtree_gap=150, horizontal_mask_gap=50, dot_font_reference_size=20 | VERIFIED | All 3 new keys confirmed at lines 8–10 |
| `node_layout_prefs_dialog.py` | Sectioned dialog with bold QLabel separators and 3 new QLineEdit fields in 3 sections | VERIFIED | `_make_section_header()` at line 14; 3 sections; all 3 new fields present; save wired via `_on_accept()` |
| `node_layout.py` | `_horizontal_margin()` reading prefs; `nuke.lastHitGroup()` at both entry points; `with current_group:` in both functions; `push_nodes_to_make_room` accepting `current_group` | VERIFIED | Lines 131, 583, 589, 633, 641, 531, 544 all confirmed by direct grep |
| `menu.py` | CMD-01 comment and 4 correct scheme command names | VERIFIED | CMD-01 comment at line 22; all 4 scheme names at lines 23–26 |
| `tests/test_node_layout_prefs.py` | Tests for 10-key DEFAULTS and round-trip behavior | VERIFIED | Confirmed present; 168-test suite passes |
| `tests/test_node_layout_prefs_dialog.py` | AST structural tests for dialog sections and fields | VERIFIED | Confirmed present; all tests pass |
| `tests/test_prefs_integration.py` | Updated tests reflecting new H-axis absolute-pref contract | VERIFIED | `TestHorizontalOnlyScheme` uses `_horizontal_margin()`; all tests pass |
| `tests/test_horizontal_margin.py` | TDD test file for `_horizontal_margin()` | VERIFIED | Confirmed present; all tests pass |
| `tests/test_group_context.py` | 8 AST tests asserting `nuke.lastHitGroup()` (not thisGroup) at both entry points | VERIFIED | Both `capture_text` strings assert `"current_group = nuke.lastHitGroup()"`; 8 tests pass |
| `.planning/phases/06-prefs-groundwork-group-fix-renames/06-UAT.md` | status: complete, passed: 6, issues: 0, gap closed | VERIFIED | `status: complete`, `passed: 6`, `issues: 0`, gap entry `status: closed`, `closed_by: "06-04-PLAN.md"` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| node_layout_prefs_dialog.py `_populate_from_prefs` | node_layout_prefs `prefs_singleton.get()` | `setText()` calls for all 10 prefs | VERIFIED | Lines 97–105: all 10 `setText` calls confirmed |
| node_layout_prefs_dialog.py `_on_accept` | node_layout_prefs `prefs_singleton.set()` | `int()` parse + validate + set for 3 new int prefs | VERIFIED | Parse at lines 110/111/118; set() at 135/136/143 |
| node_layout.py `compute_dims` | prefs `horizontal_subtree_gap` / `horizontal_mask_gap` | `_horizontal_margin(node, slot)` | VERIFIED | `side_margins_h = [_horizontal_margin(node, slot) ...]` at line 292 |
| node_layout.py `place_subtree` | prefs `horizontal_subtree_gap` / `horizontal_mask_gap` | `_horizontal_margin(node, slot)` | VERIFIED | `side_margins_h = [_horizontal_margin(node, slot) ...]` at line 411 |
| node_layout.py `layout_selected` horizontal_clearance | prefs `horizontal_subtree_gap` | `current_prefs.get("horizontal_subtree_gap")` | VERIFIED | Line 670 — no sqrt formula |
| node_layout.py `layout_upstream` | nuke.lastHitGroup() | `current_group = nuke.lastHitGroup()` — first Nuke API call | VERIFIED | Line 583; confirmed by direct grep; zero `nuke.thisGroup()` in file |
| node_layout.py `layout_selected` | nuke.lastHitGroup() | `current_group = nuke.lastHitGroup()` — first Nuke API call | VERIFIED | Line 633; confirmed by direct grep |
| node_layout.py `layout_upstream` body | `insert_dot_nodes` and `place_subtree` calls | `with current_group:` wrapping entire try block body | VERIFIED | `with current_group:` at line 589 |
| node_layout.py `layout_selected` body | `insert_dot_nodes` and `place_subtree` calls | `with current_group:` wrapping entire try block body | VERIFIED | `with current_group:` at line 641 |
| node_layout.py `push_nodes_to_make_room` | `current_group.nodes()` | `current_group` parameter passed from both entry points | VERIFIED | Lines 609 and 683 pass `current_group`; line 544 gates `current_group.nodes()` vs `nuke.allNodes()` |
| 06-UAT.md gap entry | Plan 06-04 closure record | `closed_by` and `verified_by` fields | VERIFIED | `closed_by: "06-04-PLAN.md"`, `verified_by: "UAT re-run — user confirmed pass"` |

---

### Requirements Coverage

All 7 Phase 6 requirements are claimed by plans and verified in the codebase. REQUIREMENTS.md confirms all 7 as Complete with checkboxes marked.

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| PREFS-01 | 06-01, 06-02 | User can configure horizontal gap between subtrees via prefs dialog | SATISFIED | `horizontal_subtree_gap=150` in DEFAULTS; dialog field present; engine reads via `_horizontal_margin()` |
| PREFS-02 | 06-01, 06-02 | User can configure a separate (smaller) horizontal gap for mask inputs via prefs dialog | SATISFIED | `horizontal_mask_gap=50` in DEFAULTS; dialog field present; `_horizontal_margin()` routes mask slots via `_is_mask_input()` |
| PREFS-03 | 06-01 | User can configure the Dot font reference size via prefs dialog | SATISFIED | `dot_font_reference_size=20` in DEFAULTS; Advanced section field present; saved via `_on_accept()` |
| PREFS-04 | 06-01 | Default spacing constants rebalanced (less vertical gap, more horizontal gap) | SATISFIED | `base_subtree_margin` 300 to 200; `loose_gap_multiplier` 12.0 to 8.0; `horizontal_subtree_gap=150` added |
| LAYOUT-04 | 06-03, 06-04 | When running layout commands inside a Nuke Group, Dot nodes are created inside that Group | SATISFIED | `with current_group:` wraps `insert_dot_nodes()` calls; `nuke.lastHitGroup()` ensures correct group for Group View panels; user-confirmed via UAT re-run |
| LAYOUT-05 | 06-03 | When running layout commands inside a Nuke Group, push-away logic considers only nodes within that Group | SATISFIED | `push_nodes_to_make_room()` uses `current_group.nodes()` when `current_group` is not None |
| CMD-01 | 06-03 | Compact and Loose layout scheme commands renamed with scheme name at end | SATISFIED | All 4 names verified in menu.py lines 23–26: Layout Upstream Compact, Layout Selected Compact, Layout Upstream Loose, Layout Selected Loose |

No orphaned requirements. No Phase 6 requirements exist in REQUIREMENTS.md that are unaccounted for.

---

### Anti-Patterns Found

None. Scan of all modified files (node_layout.py, node_layout_prefs.py, node_layout_prefs_dialog.py, menu.py, tests/test_group_context.py, tests/test_node_layout_prefs.py, tests/test_horizontal_margin.py, tests/test_prefs_integration.py, 06-UAT.md) found no TODO/FIXME/HACK/PLACEHOLDER patterns, no empty implementations, and no stub returns. The two `return []` occurrences in node_layout.py are valid defensive early-returns guarded by `_hides_inputs(node)`.

---

### Human Verification Required

All four human verification items were identified in the previous verification pass. Item 3 (Group View context) has since been confirmed passing by the user during the Plan 06-05 UAT re-run. Items 1, 2, and 4 remain below for completeness as they require a live Nuke session.

#### 1. Prefs Dialog Visual Appearance

**Test:** In Nuke, open the preferences dialog. Inspect the three section headers.
**Expected:** "Spacing", "Scheme Multipliers", and "Advanced" labels appear in bold with spacer rows between them. No bordered QGroupBox frames are visible. The ten fields are grouped correctly under their respective sections.
**Why human:** PySide6 rendering of bold QLabel fonts and QFormLayout spacing requires a display server and live Nuke session to confirm visual distinction.

#### 2. Group Context — Ctrl-Enter Navigation

**Test:** Ctrl-Enter into a Nuke Group. Select a node tree inside and run "Layout Upstream". Then exit the Group and inspect the root-level DAG.
**Expected:** No new Dot nodes appear at root level. All new Dot nodes are contained within the Group.
**Why human:** Requires a live Nuke session with an active Group context.

#### 3. Group Context — Group View Panel Navigation (confirmed by user)

**Test:** Open a Nuke Group via the Group View panel (inline expansion, not Ctrl-Enter). Select a node tree inside and run "Layout Upstream". Inspect root-level DAG.
**Expected:** No new Dot nodes appear at root level. All new Dot nodes are contained within the Group.
**Status:** User confirmed pass during Plan 06-05 UAT re-run. This item is closed.

#### 4. Push-Away Scope Inside Group

**Test:** Inside an open Nuke Group with several unrelated nodes, run a layout command that grows the subtree. Verify only nodes inside the Group are pushed, and root-level nodes are undisturbed.
**Expected:** Nodes inside the Group outside the subtree are pushed; root-level nodes do not move.
**Why human:** Requires a live Nuke session with both a Group context and root-level nodes present simultaneously.

---

### Gaps Summary

No gaps. All 14 truths are VERIFIED, all 10 artifacts are substantive and wired, all 11 key links are confirmed, and all 7 requirements are satisfied. Plan 06-05 closed the UAT loop — the user confirmed in a live Nuke session that Dot nodes created during layout inside a Group View panel land inside the Group. UAT.md is updated to status: complete with 6/6 tests passing.

---

_Verified: 2026-03-09T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
