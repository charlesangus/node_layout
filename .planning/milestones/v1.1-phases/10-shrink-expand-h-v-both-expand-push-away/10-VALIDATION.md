---
phase: 10
slug: shrink-expand-h-v-both-expand-push-away
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python `unittest` (stdlib) |
| **Config file** | none |
| **Quick run command** | `python3 -m unittest tests.test_scale_nodes tests.test_scale_nodes_axis` |
| **Full suite command** | `python3 -m unittest discover -s tests` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m unittest tests.test_scale_nodes tests.test_scale_nodes_axis`
- **After every plan wave:** Run `python3 -m unittest discover -s tests`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-W0-01 | W0 | 0 | SCALE-01 | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestAxisScalingBehavior.test_h_axis_leaves_dy_unchanged` | ❌ W0 | ⬜ pending |
| 10-W0-02 | W0 | 0 | SCALE-01 | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestAxisScalingBehavior.test_v_axis_leaves_dx_unchanged` | ❌ W0 | ⬜ pending |
| 10-W0-03 | W0 | 0 | SCALE-01 | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestAxisScalingBehavior.test_both_axis_unchanged` | ❌ W0 | ⬜ pending |
| 10-W0-04 | W0 | 0 | SCALE-01 | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestAxisStateBehavior.test_h_axis_only_updates_h_scale` | ❌ W0 | ⬜ pending |
| 10-W0-05 | W0 | 0 | SCALE-01 | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestAxisStateBehavior.test_v_axis_only_updates_v_scale` | ❌ W0 | ⬜ pending |
| 10-W0-06 | W0 | 0 | SCALE-01 | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestAxisScalingBehavior.test_snap_floor_not_applied_to_unchanged_axis` | ❌ W0 | ⬜ pending |
| 10-W0-07 | W0 | 0 | SCALE-02 | AST | `python3 -m unittest tests.test_scale_nodes_axis.TestNewCommandsAST` | ❌ W0 | ⬜ pending |
| 10-W0-08 | W0 | 0 | SCALE-02 | AST | `python3 -m unittest tests.test_scale_nodes_axis.TestRepeatLastScaleAST` | ❌ W0 | ⬜ pending |
| 10-W0-09 | W0 | 0 | SCALE-02 | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestRepeatLastScaleBehavior.test_last_fn_set_after_call` | ❌ W0 | ⬜ pending |
| 10-W0-10 | W0 | 0 | SCALE-02 | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestRepeatLastScaleBehavior.test_repeat_calls_last_fn` | ❌ W0 | ⬜ pending |
| 10-W0-11 | W0 | 0 | SCALE-02 | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestRepeatLastScaleBehavior.test_repeat_noop_when_none` | ❌ W0 | ⬜ pending |
| 10-W0-12 | W0 | 0 | SCALE-03 | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestExpandPushAway.test_expand_h_calls_push` | ❌ W0 | ⬜ pending |
| 10-W0-13 | W0 | 0 | SCALE-03 | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestExpandPushAway.test_expand_v_calls_push` | ❌ W0 | ⬜ pending |
| 10-W0-14 | W0 | 0 | SCALE-03 | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestExpandPushAway.test_shrink_h_no_push` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_scale_nodes_axis.py` — all new tests for SCALE-01, SCALE-02, SCALE-03 (entire new test file covering axis parameter behavior, state write-back, repeat-last-scale, and expand push-away)

*No framework install needed — `unittest` is stdlib.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Menu commands appear in correct groups with correct labels | SCALE-02 | Nuke UI introspection not available in unit tests | Launch Nuke, open DAG menu, verify 8 new entries appear grouped by scope then axis |
| Modifier keys on existing shortcuts trigger axis variants | SCALE-02 | Keyboard shortcut binding is Nuke host-dependent | In Nuke, hold modifier while pressing existing shrink/expand shortcut; verify axis-specific variant fires |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
