# Roadmap: node_layout

## Milestones

- ✅ **v1.0 Quality & Preferences** — Phases 1-5 (shipped 2026-03-05)
- ✅ **v1.1 Layout Engine & State** — Phases 6-12 (shipped 2026-03-17)
- 🚧 **v1.2 CI/CD** — Phases 13-14 (in progress)

## Phases

<details>
<summary>✅ v1.0 Quality & Preferences (Phases 1-5) — SHIPPED 2026-03-05</summary>

- [x] Phase 1: Code Quality (2/2 plans) — completed 2026-03-04
- [x] Phase 2: Bug Fixes (3/3 plans) — completed 2026-03-04
- [x] Phase 3: Undo & Reliability (1/1 plan) — completed 2026-03-04
- [x] Phase 4: Preferences System (3/3 plans) — completed 2026-03-04
- [x] Phase 5: New Commands & Scheme (4/4 plans) — completed 2026-03-05

Full archive: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 Layout Engine & State (Phases 6-12) — SHIPPED 2026-03-17</summary>

- [x] Phase 6: Prefs Groundwork + Group Fix + Renames (5/5 plans) — completed 2026-03-08
- [x] Phase 7: Per-Node State Storage (7/7 plans) — completed 2026-03-10
- [x] Phase 8: Dot Font-Size Margin Scaling (2/2 plans) — completed 2026-03-11
- [x] Phase 9: Multi-Input Fan Alignment + Mask Side-Swap (2/2 plans) — completed 2026-03-12
- [x] Phase 10: Shrink/Expand H/V/Both + Expand Push-Away (2/2 plans) — completed 2026-03-12
- [x] Phase 11: Horizontal B-Spine Layout (5/5 plans) — completed 2026-03-13
- [x] Phase 11.1: Fix Horizontal Layout Functionality (3/3 plans) — completed 2026-03-15 (INSERTED)
- [x] Phase 11.2: Fix Horizontal Layout Bbox (2/2 plans) — completed 2026-03-16 (INSERTED)
- [x] Phase 12: Fix Fan Layout Logic (2/2 plans) — completed 2026-03-17 (INSERTED)

Full archive: `.planning/milestones/v1.1-ROADMAP.md`

</details>

### 🚧 v1.2 CI/CD (In Progress)

**Milestone Goal:** Add a CI/CD system that automatically tests on every push and produces reliable versioned release artifacts on tag push.

- [x] **Phase 13: Tooling + CI** — pyproject.toml with Ruff config and GitHub Actions CI workflow (completed 2026-03-17)
- [ ] **Phase 14: Release Workflow** — Tag-triggered release workflow producing versioned ZIP and GitHub Release

## Phase Details

### Phase 13: Tooling + CI
**Goal**: Every push and pull request is automatically linted and tested with results visible in GitHub
**Depends on**: Nothing (first phase of v1.2)
**Requirements**: TOOL-01, CI-01, CI-02, CI-03
**Success Criteria** (what must be TRUE):
  1. `pyproject.toml` exists at the repo root with Ruff configured (line length, E/F/W/B/I/SIM rules, per-file exceptions for `menu.py`)
  2. Pushing a commit to any branch triggers the CI workflow and runs all 276 pytest tests
  3. Pushing a commit to any branch triggers Ruff linting and reports any violations
  4. A pull request shows a green or red check from the CI workflow before merging
**Plans:** 3/3 plans complete

Plans:
- [ ] 13-01-PLAN.md — pyproject.toml + menu.py wrapping + portable test paths
- [ ] 13-02-PLAN.md — Fix all Ruff violations across source and test files
- [ ] 13-03-PLAN.md — GitHub Actions CI workflow

### Phase 14: Release Workflow
**Goal**: Pushing a version tag automatically produces a tested, versioned ZIP and publishes it as a GitHub Release
**Depends on**: Phase 13
**Requirements**: REL-01, REL-02, REL-03, REL-04
**Success Criteria** (what must be TRUE):
  1. Pushing a `v*` tag triggers the release workflow
  2. The release workflow runs tests and linting before building; it does not publish if either fails
  3. A versioned ZIP named `node_layout-vX.Y.zip` containing all plugin `.py` files, `README.md`, and `LICENSE` is attached to the release
  4. A GitHub Release is published automatically with the ZIP attached and auto-generated release notes
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Code Quality | v1.0 | 2/2 | Complete | 2026-03-04 |
| 2. Bug Fixes | v1.0 | 3/3 | Complete | 2026-03-04 |
| 3. Undo & Reliability | v1.0 | 1/1 | Complete | 2026-03-04 |
| 4. Preferences System | v1.0 | 3/3 | Complete | 2026-03-04 |
| 5. New Commands & Scheme | v1.0 | 4/4 | Complete | 2026-03-05 |
| 6. Prefs Groundwork + Group Fix + Renames | v1.1 | 5/5 | Complete | 2026-03-08 |
| 7. Per-Node State Storage | v1.1 | 7/7 | Complete | 2026-03-10 |
| 8. Dot Font-Size Margin Scaling | v1.1 | 2/2 | Complete | 2026-03-11 |
| 9. Multi-Input Fan Alignment + Mask Side-Swap | v1.1 | 2/2 | Complete | 2026-03-12 |
| 10. Shrink/Expand H/V/Both + Expand Push-Away | v1.1 | 2/2 | Complete | 2026-03-12 |
| 11. Horizontal B-Spine Layout | v1.1 | 5/5 | Complete | 2026-03-13 |
| 11.1. Fix Horizontal Layout Functionality (INSERTED) | v1.1 | 3/3 | Complete | 2026-03-15 |
| 11.2. Fix Horizontal Layout Bbox (INSERTED) | v1.1 | 2/2 | Complete | 2026-03-16 |
| 12. Fix Fan Layout Logic (INSERTED) | v1.1 | 2/2 | Complete | 2026-03-17 |
| 13. Tooling + CI | 3/3 | Complete   | 2026-03-17 | - |
| 14. Release Workflow | v1.2 | 0/? | Not started | - |
