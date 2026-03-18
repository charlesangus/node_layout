# Requirements: node_layout

**Defined:** 2026-03-17
**Core Value:** Layout operations must be reliable, undoable, and configurable — users need to trust the tool won't silently misbehave.

## v1.2 Requirements

Requirements for the CI/CD milestone. Each maps to roadmap phases.

### Tooling

- [x] **TOOL-01**: Project has `pyproject.toml` with Ruff configuration (line length, E/F/W/B/I/SIM rules, per-file exceptions for `menu.py`)

### CI

- [x] **CI-01**: GitHub Actions CI workflow runs pytest on every push and pull request
- [x] **CI-02**: GitHub Actions CI workflow runs Ruff linting on every push and pull request
- [x] **CI-03**: CI workflow reports pass/fail status on pull requests

### Release

- [x] **REL-01**: Release workflow triggers on `v*` git tag push
- [x] **REL-02**: Release workflow gates on passing tests and linting before building artifact
- [x] **REL-03**: Release workflow produces a versioned ZIP (`node_layout-vX.Y.zip`) containing all plugin `.py` files, `README.md`, and `LICENSE`
- [x] **REL-04**: Release workflow publishes a GitHub Release with the ZIP attached and auto-generated release notes

## Future Requirements

(None identified at this time)

## Out of Scope

| Feature | Reason |
|---------|--------|
| PyPI publishing | Not a Python package; users install manually into ~/.nuke/ |
| Docker-based Nuke testing | No headless Nuke license available; stub-based tests are sufficient |
| Automated versioning / changelog generation | Git tags + auto-release notes are sufficient for now |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TOOL-01 | Phase 13 | Complete |
| CI-01 | Phase 13 | Complete |
| CI-02 | Phase 13 | Complete |
| CI-03 | Phase 13 | Complete |
| REL-01 | Phase 14 | Complete |
| REL-02 | Phase 14 | Complete |
| REL-03 | Phase 14 | Complete |
| REL-04 | Phase 14 | Complete |

**Coverage:**
- v1.2 requirements: 8 total
- Mapped to phases: 8
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-17*
*Last updated: 2026-03-17 after roadmap creation*
