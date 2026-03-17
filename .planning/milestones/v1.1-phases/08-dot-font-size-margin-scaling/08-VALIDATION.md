---
phase: 8
slug: dot-font-size-margin-scaling
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python `unittest` (stdlib) |
| **Config file** | none — tests run via `unittest discover` or direct execution |
| **Quick run command** | `python3 -m unittest discover -s /workspace/tests -p "test_dot_font_scale.py" -v` |
| **Full suite command** | `python3 -m unittest discover -s /workspace/tests -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m unittest discover -s /workspace/tests -p "test_dot_font_scale.py" -v`
- **After every plan wave:** Run `python3 -m unittest discover -s /workspace/tests -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 8-01-01 | 01 | 0 | LAYOUT-03 | unit | `python3 -m unittest tests.test_dot_font_scale.TestDotFontScaleUnit.test_no_dot_returns_1` | ❌ W0 | ⬜ pending |
| 8-01-02 | 01 | 0 | LAYOUT-03 | unit | `python3 -m unittest tests.test_dot_font_scale.TestDotFontScaleUnit.test_unlabeled_dot_chain_returns_1` | ❌ W0 | ⬜ pending |
| 8-01-03 | 01 | 0 | LAYOUT-03 | unit | `python3 -m unittest tests.test_dot_font_scale.TestDotFontScaleUnit.test_labeled_dot_font_40_reference_20` | ❌ W0 | ⬜ pending |
| 8-01-04 | 01 | 0 | LAYOUT-03 | unit | `python3 -m unittest tests.test_dot_font_scale.TestDotFontScaleUnit.test_floor_at_1` | ❌ W0 | ⬜ pending |
| 8-01-05 | 01 | 0 | LAYOUT-03 | unit | `python3 -m unittest tests.test_dot_font_scale.TestDotFontScaleUnit.test_cap_at_4` | ❌ W0 | ⬜ pending |
| 8-01-06 | 01 | 0 | LAYOUT-03 | unit | `python3 -m unittest tests.test_dot_font_scale.TestDotFontScaleUnit.test_walk_skips_unlabeled_finds_labeled` | ❌ W0 | ⬜ pending |
| 8-01-07 | 01 | 0 | LAYOUT-03 | unit | `python3 -m unittest tests.test_dot_font_scale.TestDotFontScaleUnit.test_walk_stops_at_non_dot` | ❌ W0 | ⬜ pending |
| 8-01-08 | 01 | 0 | LAYOUT-03 | unit | `python3 -m unittest tests.test_dot_font_scale.TestDotFontScaleUnit.test_missing_knob_fallback` | ❌ W0 | ⬜ pending |
| 8-02-01 | 02 | 1 | LAYOUT-03 | unit | `python3 -m unittest tests.test_dot_font_scale.TestSubtreeMarginFontScale.test_font_scale_applies` | ❌ W0 | ⬜ pending |
| 8-02-02 | 02 | 1 | LAYOUT-03 | unit | `python3 -m unittest tests.test_dot_font_scale.TestHorizontalMarginFontScale.test_font_scale_applies` | ❌ W0 | ⬜ pending |
| 8-02-03 | 02 | 1 | LAYOUT-03 | unit | `python3 -m unittest tests.test_dot_font_scale.TestNoRegression.test_default_font_no_change` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `/workspace/tests/test_dot_font_scale.py` — stubs for all LAYOUT-03 test IDs above (new file)

*All Wave 0 tests are in a single new file; existing test infrastructure covers Phase 8 fully.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `note_font_size` knob name resolves correctly in live Nuke | LAYOUT-03 | Nuke runtime required; cannot mock knob discovery in unit tests | Create a Dot node in Nuke, set a label and a non-default font size (e.g. 40), then run layout and confirm subtree margin is visibly wider than a default-font Dot |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
