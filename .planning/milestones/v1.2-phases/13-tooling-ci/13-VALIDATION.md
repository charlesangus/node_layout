---
phase: 13
slug: tooling-ci
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already installed) |
| **Config file** | none — Wave 0 creates `pyproject.toml` |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v` + `ruff check .`
- **Before `/gsd:verify-work`:** Full suite must be green + `ruff check .` must exit 0 + push to GitHub and confirm green check
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | TOOL-01 | smoke | `python -c "import tomllib; c=tomllib.load(open('pyproject.toml','rb')); assert c['tool']['ruff']['line-length']==100"` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 1 | TOOL-01 | smoke | `ruff check .` (exits 0) | ❌ W0 | ⬜ pending |
| 13-02-01 | 02 | 1 | (prereq) | unit | `pytest tests/ -v` (all pass) | ✅ after fix | ⬜ pending |
| 13-03-01 | 03 | 2 | CI-01, CI-02, CI-03 | manual | Push to GitHub, verify green check in Actions tab | ✅ after creation | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` — must exist before `ruff check .` can run (TOOL-01)
- [ ] 14 test files with `/workspace/` paths fixed — must be portable before CI-01 can pass

*Wave 0 creates the infrastructure that enables all subsequent automated verification.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CI workflow runs pytest on push/PR | CI-01 | Requires actual GitHub push to trigger Actions | Push any branch; check Actions tab shows "Run tests" step green |
| CI workflow runs Ruff on push/PR | CI-02 | Requires actual GitHub push to trigger Actions | Push any branch; check Actions tab shows "Lint with Ruff" step green |
| PR shows green/red check | CI-03 | Requires actual GitHub PR | Open a test PR; verify green checkmark appears before merge button |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
