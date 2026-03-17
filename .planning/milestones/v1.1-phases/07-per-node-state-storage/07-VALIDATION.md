---
phase: 7
slug: per-node-state-storage
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | unittest (stdlib) — pytest not installed |
| **Config file** | none |
| **Quick run command** | `python3.11 -m unittest discover -s /workspace/tests -p "*.py" -q` |
| **Full suite command** | `python3.11 -m unittest discover -s /workspace/tests -p "*.py" -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3.11 -m unittest discover -s /workspace/tests -p "*.py" -q`
- **After every plan wave:** Run `python3.11 -m unittest discover -s /workspace/tests -p "*.py" -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 7-W0-01 | 01 | 0 | STATE-01, STATE-02, STATE-03, STATE-04 | unit+structural | `python3.11 -m unittest tests.test_node_layout_state tests.test_state_integration -q` | ❌ W0 | ⬜ pending |
| 7-01-01 | 01 | 1 | STATE-01, STATE-02 | unit (pure Python) | `python3.11 -m unittest tests.test_node_layout_state -q` | ❌ W0 | ⬜ pending |
| 7-02-01 | 02 | 1 | STATE-01 | structural (AST) | `python3.11 -m unittest tests.test_state_integration -q` | ❌ W0 | ⬜ pending |
| 7-03-01 | 03 | 1 | STATE-03 | structural (AST) | `python3.11 -m unittest tests.test_state_integration -q` | ❌ W0 | ⬜ pending |
| 7-04-01 | 04 | 2 | STATE-04 | unit+structural | `python3.11 -m unittest tests.test_state_integration -q` | ❌ W0 | ⬜ pending |
| 7-05-01 | 05 | 2 | STATE-01, STATE-03 | structural (AST) | `python3.11 -m unittest tests.test_state_integration -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `/workspace/node_layout_state.py` — new helper module (test target for pure-Python tests)
- [ ] `/workspace/tests/test_node_layout_state.py` — unit tests for STATE-01/02/03/04 (pure Python + Nuke stub)
- [ ] `/workspace/tests/test_state_integration.py` — AST structural tests for integration points in `node_layout.py`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hidden tab+knob visible in Nuke Script Editor after layout | STATE-01 | Requires live Nuke runtime | Run layout command, open Script Editor, inspect `node['node_layout_state'].value()` |
| State persists after File > Save + File > Open in Nuke | STATE-02 | Requires live Nuke runtime | Run layout, save .nk, reopen, verify knob values unchanged |
| Re-layout replays stored scheme without specifying it | STATE-03 | Requires live Nuke runtime | Layout Compact → close → run Layout (no scheme) → verify Compact applied |
| Explicit scheme overrides stored scheme | STATE-03 | Requires live Nuke runtime | Layout Compact → run Layout Loose → verify Loose stored + applied |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
