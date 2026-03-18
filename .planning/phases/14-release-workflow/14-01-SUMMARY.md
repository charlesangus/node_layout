---
phase: 14-release-workflow
plan: 01
subsystem: infra
tags: [github-actions, ci-cd, release, zip, softprops-action-gh-release]

# Dependency graph
requires:
  - phase: 13-tooling-ci
    provides: "CI workflow pattern (ubuntu-24.04, Python 3.11, ruff + pytest) mirrored verbatim"
provides:
  - "Tag-triggered GitHub Actions release workflow"
  - "Automated ZIP build of plugin distribution artifact"
  - "GitHub Release publish with auto-generated notes"
affects: [release process, future tagging workflow]

# Tech tracking
tech-stack:
  added: [softprops/action-gh-release@v2]
  patterns: [two-job workflow with test gate before build, hardcoded file list in ZIP step]

key-files:
  created: [.github/workflows/release.yml]
  modified: []

key-decisions:
  - "Two-job structure: test job runs ruff + pytest; build job gates on needs: test (REL-02)"
  - "ZIP file list hardcoded to 9 files — no globs to avoid accidental inclusion of future files"
  - "ZIP named node_layout-${{ github.ref_name }}.zip — keeps v prefix per user decision (e.g. node_layout-v1.2.zip)"
  - "Release published immediately (no draft) via softprops/action-gh-release@v2 with generate_release_notes: true"
  - "permissions: contents: write on build job only"

patterns-established:
  - "Tag trigger pattern: on.push.tags with v* glob"
  - "Test-gate pattern: needs: [test-job-name] on build/deploy jobs"

requirements-completed: [REL-01, REL-02, REL-03, REL-04]

# Metrics
duration: 3min
completed: 2026-03-18
---

# Phase 14 Plan 01: Release Workflow Summary

**GitHub Actions release workflow triggered by v* tags: runs ruff + pytest gate, builds node_layout-vX.Y.Z.zip from 9 hardcoded files, publishes GitHub Release with auto-generated notes via softprops/action-gh-release@v2**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-18T00:25:24Z
- **Completed:** 2026-03-18T00:28:00Z
- **Tasks:** 1 executed + 1 auto-approved checkpoint
- **Files modified:** 1

## Accomplishments
- Created `.github/workflows/release.yml` with tag trigger on `v*` pattern (REL-01)
- `test` job mirrors ci.yml exactly: ubuntu-24.04, Python 3.11, ruff check + pytest (REL-02)
- `build` job gates on `needs: test`, creates `node_layout/` directory, copies 9 hardcoded files, ZIPs and publishes GitHub Release (REL-03, REL-04)
- Auto-generated release notes via `generate_release_notes: true` — no manual authoring needed

## Task Commits

Each task was committed atomically:

1. **Task 1: Create release workflow with test gate** - `4ce554c` (feat)
2. **Task 2: Verify release workflow structure** - auto-approved checkpoint (no commit)

## Files Created/Modified
- `.github/workflows/release.yml` - Tag-triggered release workflow with test gate and ZIP distribution build

## Decisions Made
- Hardcoded 9-file list in `cp` command (not glob) to prevent accidental inclusion of test files or future non-distribution files
- `permissions: contents: write` placed on `build` job only, not workflow-level
- No `name:` override on release step — defaults to tag name (e.g. `v1.2.0`)
- No `draft: true` — releases publish immediately when workflow completes

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. The workflow uses `GITHUB_TOKEN` (automatically provided by GitHub Actions) for release creation.

## Next Phase Readiness
- Release workflow is complete and ready for end-to-end smoke testing
- To test: push a `v*` tag (e.g. `git tag v0.1.0 && git push origin v0.1.0`) and verify the Actions tab shows both jobs completing and a GitHub Release with `node_layout-v0.1.0.zip` attached
- Phase 14 is the final phase — no further phases planned

---
*Phase: 14-release-workflow*
*Completed: 2026-03-18*
