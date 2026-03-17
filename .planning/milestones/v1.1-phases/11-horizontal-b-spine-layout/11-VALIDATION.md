---
phase: 11
slug: horizontal-b-spine-layout
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python unittest (stdlib) |
| **Config file** | none — direct `python3 -m unittest discover tests/` |
| **Quick run command** | `python3 -m unittest tests/test_horizontal_layout.py -v` |
| **Full suite command** | `python3 -m unittest discover tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m unittest tests/test_horizontal_layout.py -q`
- **After every plan wave:** Run `python3 -m unittest discover tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green (only pre-existing 4 errors from test_scale_nodes_axis nuke stub issue allowed)
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 0 | HORIZ-01,02,03 | unit stub | `python3 -m unittest tests/test_horizontal_layout.py -q` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 1 | HORIZ-01 | unit | `python3 -m unittest tests/test_horizontal_layout.py::TestHorizontalSpine -v` | ❌ W0 | ⬜ pending |
| 11-02-02 | 02 | 1 | HORIZ-01 | unit | `python3 -m unittest tests/test_horizontal_layout.py::TestOutputDot -v` | ❌ W0 | ⬜ pending |
| 11-02-03 | 02 | 1 | HORIZ-01 | unit | `python3 -m unittest tests/test_horizontal_layout.py::TestMaskKink -v` | ❌ W0 | ⬜ pending |
| 11-02-04 | 02 | 1 | HORIZ-01 | unit | `python3 -m unittest tests/test_horizontal_layout.py::TestSideInputPlacement -v` | ❌ W0 | ⬜ pending |
| 11-03-01 | 03 | 2 | HORIZ-02 | unit | `python3 -m unittest tests/test_horizontal_layout.py::TestHorizontalAST -v` | ❌ W0 | ⬜ pending |
| 11-03-02 | 03 | 2 | HORIZ-03 | unit | `python3 -m unittest tests/test_horizontal_layout.py::TestModeReplay -v` | ❌ W0 | ⬜ pending |
| 11-03-03 | 03 | 2 | HORIZ-03 | unit | `python3 -m unittest tests/test_horizontal_layout.py::TestHorizontalAST -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_horizontal_layout.py` — stubs for HORIZ-01, HORIZ-02, HORIZ-03 (TestHorizontalSpine, TestOutputDot, TestMaskKink, TestSideInputPlacement, TestHorizontalAST, TestModeReplay)
- [ ] Framework: stdlib unittest, no install needed

*Existing infrastructure covers all phase requirements — only new test file needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual DAG layout in Nuke | HORIZ-01 | Requires live Nuke session | Open Nuke, create linear chain, run "Layout Upstream Horizontal", verify spine goes left-to-right |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
