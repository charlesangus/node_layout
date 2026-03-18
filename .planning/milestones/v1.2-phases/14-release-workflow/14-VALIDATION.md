---
phase: 14
slug: release-workflow
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | `pyproject.toml` (Ruff config only; pytest uses default discovery) |
| **Quick run command** | `pytest tests/ -v` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Inspect `release.yml` YAML structure manually
- **After every plan wave:** N/A — single-plan phase
- **Before `/gsd:verify-work`:** End-to-end smoke test (push a `v*` tag, verify release appears on GitHub)
- **Max feedback latency:** ~30 seconds (YAML inspection)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 1 | REL-01 | manual | Inspect `.github/workflows/release.yml` trigger block | ❌ Wave 0 | ⬜ pending |
| 14-01-02 | 01 | 1 | REL-02 | manual | Inspect workflow YAML for `needs: test` on build job | ❌ Wave 0 | ⬜ pending |
| 14-01-03 | 01 | 1 | REL-03 | manual | Inspect ZIP build steps in workflow YAML | ❌ Wave 0 | ⬜ pending |
| 14-01-04 | 01 | 1 | REL-04 | manual | Inspect `softprops/action-gh-release` step with `generate_release_notes: true` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `.github/workflows/release.yml` — the only deliverable; does not exist yet

*No test files needed — workflow validation is structural inspection + live smoke test.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `v*` tag triggers release workflow | REL-01 | GitHub Actions workflow can't be unit-tested | Inspect `on: push: tags: ['v*']` trigger in release.yml |
| build job requires test job to pass | REL-02 | GitHub Actions job dependencies can't be unit-tested | Inspect `needs: test` on build job in release.yml |
| ZIP contains correct files with `node_layout/` prefix | REL-03 | Requires live GitHub Actions run | Push `v*` tag; inspect release asset contents |
| GitHub Release published with ZIP and auto-notes | REL-04 | Requires live GitHub Actions run | Inspect GitHub Releases page after tag push |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
