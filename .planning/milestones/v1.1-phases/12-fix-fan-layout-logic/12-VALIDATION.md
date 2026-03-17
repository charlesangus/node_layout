---
phase: 12
slug: fix-fan-layout-logic
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python `unittest` (stdlib, no install needed) |
| **Config file** | none — direct module execution |
| **Quick run command** | `python3 -m unittest tests.test_fan_alignment -v` |
| **Full suite command** | `python3 -m unittest discover -s tests -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m unittest tests.test_fan_alignment -v`
- **After every plan wave:** Run `python3 -m unittest discover -s tests -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 0 | Bug1 Y | unit | `python3 -m unittest tests.test_fan_alignment.TestPlaceSubtreeFanRoots.test_fan_dot_row_y_in_gap_not_on_consumer -v` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 0 | Bug2 X | unit | `python3 -m unittest tests.test_fan_alignment.TestPlaceSubtreeFanRoots.test_fan_a1_x_clears_b_subtree_right_edge -v` | ❌ W0 | ⬜ pending |
| 12-01-03 | 01 | 0 | dims W | unit | `python3 -m unittest tests.test_fan_alignment.TestComputeDimsFanWidth.test_compute_dims_fan_w_accounts_for_b_overhang -v` | ❌ W0 | ⬜ pending |
| 12-02-01 | 02 | 1 | Bug1 Y | unit | `python3 -m unittest tests.test_fan_alignment.TestPlaceSubtreeFanRoots.test_fan_dot_row_y_in_gap_not_on_consumer -v` | ✅ | ⬜ pending |
| 12-02-02 | 02 | 1 | Bug2 X | unit | `python3 -m unittest tests.test_fan_alignment.TestPlaceSubtreeFanRoots.test_fan_a1_x_clears_b_subtree_right_edge -v` | ✅ | ⬜ pending |
| 12-02-03 | 02 | 1 | dims W | unit | `python3 -m unittest tests.test_fan_alignment.TestComputeDimsFanWidth.test_compute_dims_fan_w_accounts_for_b_overhang -v` | ✅ | ⬜ pending |
| 12-02-04 | 02 | 1 | regression | regression | `python3 -m unittest tests.test_fan_alignment -v` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_fan_alignment.py` — add `test_fan_dot_row_y_in_gap_not_on_consumer` to `TestPlaceSubtreeFanRoots`
- [ ] `tests/test_fan_alignment.py` — add `test_fan_a1_x_clears_b_subtree_right_edge` to `TestPlaceSubtreeFanRoots`
- [ ] `tests/test_fan_alignment.py` — add new class `TestComputeDimsFanWidth` with `test_compute_dims_fan_w_accounts_for_b_overhang`

All three tests must be RED (failing) after Wave 0 is complete — they exist to be fixed in Wave 1.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual Dot row placement in gap | Bug 1 | Requires Nuke DAG visual inspection | Run layout on fan node; confirm Dot row is visually in the gap, not overlapping consumer |
| A1/A2 subtree no overlap with B subtree | Bug 2 | Requires Nuke DAG visual inspection | Run layout on fan node with wide B subtree; confirm A1 left edge clears B right edge |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
