---
phase: 9
slug: multi-input-fan-alignment-mask-side-swap
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python `unittest` (stdlib) |
| **Config file** | none |
| **Quick run command** | `python3 -m unittest tests/test_fan_alignment.py` |
| **Full suite command** | `python3 -m unittest discover tests` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m unittest tests/test_fan_alignment.py`
- **After every plan wave:** Run `python3 -m unittest discover tests`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 3 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 9-01-01 | 01 | 0 | LAYOUT-01 | unit | `python3 -m unittest tests/test_fan_alignment.py` | ❌ W0 | ⬜ pending |
| 9-01-02 | 01 | 1 | LAYOUT-01 | unit | `python3 -m unittest tests/test_fan_alignment.py -k test_fan_active_predicate` | ✅ | ⬜ pending |
| 9-01-03 | 01 | 1 | LAYOUT-01 | unit | `python3 -m unittest tests/test_fan_alignment.py -k test_compute_dims_fan_height` | ✅ | ⬜ pending |
| 9-01-04 | 01 | 1 | LAYOUT-01 | unit | `python3 -m unittest tests/test_fan_alignment.py -k test_fan_roots_same_y` | ✅ | ⬜ pending |
| 9-01-05 | 01 | 1 | LAYOUT-01 | unit | `python3 -m unittest tests/test_fan_alignment.py -k test_fan_dot_row_uniform_y` | ✅ | ⬜ pending |
| 9-01-06 | 01 | 1 | LAYOUT-01 | unit | `python3 -m unittest tests/test_fan_alignment.py -k test_two_input_no_fan` | ✅ | ⬜ pending |
| 9-02-01 | 02 | 2 | LAYOUT-02 | unit | `python3 -m unittest tests/test_fan_alignment.py -k test_mask_left_of_consumer` | ✅ | ⬜ pending |
| 9-02-02 | 02 | 2 | LAYOUT-02 | unit | `python3 -m unittest tests/test_fan_alignment.py -k test_mask_x_formula` | ✅ | ⬜ pending |
| 9-02-03 | 02 | 2 | LAYOUT-02 | unit | `python3 -m unittest tests/test_fan_alignment.py -k test_mask_right_when_no_fan` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_fan_alignment.py` — 8 RED test stubs covering LAYOUT-01 and LAYOUT-02

*Wave 0 creates the test file before implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Fan layout visually correct in Nuke DAG | LAYOUT-01 | Requires live Nuke session | Create a Merge node with 3+ non-mask inputs, run layout, verify all input roots are at the same Y level with a uniform Dot row |
| Mask appears LEFT in Nuke DAG | LAYOUT-02 | Requires live Nuke session | Create a Merge node with 3+ non-mask inputs + mask, run layout, verify mask subtree is to the left of consumer |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 3s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
