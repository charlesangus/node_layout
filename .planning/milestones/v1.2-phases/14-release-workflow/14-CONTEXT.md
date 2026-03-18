# Phase 14: Release Workflow - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a GitHub Actions release workflow that triggers on `v*` tag push, gates on passing tests and linting, builds a versioned ZIP, and publishes a GitHub Release. No changes to CI workflow, prefs, or plugin logic.

</domain>

<decisions>
## Implementation Decisions

### CI gate strategy
- Two separate jobs: `test` job runs Ruff + pytest; `build` job has `needs: test`
- `build` job only runs if `test` passes — REL-02 gating enforced
- Same runner and Python version as CI: ubuntu-24.04, Python 3.11
- Ruff + pytest both required in `test` job (not pytest-only like anchors)

### ZIP structure
- Create a `node_layout/` directory, copy files into it, then ZIP that folder
- Contents: `node_layout.py`, `node_layout_state.py`, `util.py`, `node_layout_prefs.py`, `node_layout_prefs_dialog.py`, `menu.py`, `make_room.py`, `README.md`, `LICENSE`
- File list is hardcoded (not a glob) — no accidental inclusion of future non-plugin files
- Tests excluded — ZIP is user-facing distribution only
- ZIP named `node_layout-${GITHUB_REF_NAME}.zip` (keeps `v` prefix, e.g. `node_layout-v1.2.zip`)
- Install path intent: user drops `node_layout/` into `~/.nuke/` and adds `nuke.pluginAddPath('node_layout')` to init.py

### Release notes
- `generate_release_notes: true` via softprops/action-gh-release@v2
- GitHub auto-generates from commits/PRs since last tag — no manual authoring required

### Publish behavior
- Release published immediately when workflow completes — no draft step
- `permissions: contents: write` required on the workflow

### Claude's Discretion
- Exact pip install command (whether to pin ruff/pytest versions)
- Release name format (tag name vs. custom string)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Reference implementation
- `.github/workflows/ci.yml` — Existing CI workflow; release workflow should mirror job structure and tooling versions

### Requirements
- `.planning/REQUIREMENTS.md` §REL-01–REL-04 — Exact acceptance criteria for the release workflow

No external specs — requirements are fully captured in decisions above and REQUIREMENTS.md.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.github/workflows/ci.yml`: Checkout → Python 3.11 → `pip install ruff pytest` → `ruff check .` → `pytest tests/ -v` — copy this pattern verbatim for the `test` job in release workflow

### Established Patterns
- ubuntu-24.04 runner, Python 3.11, no pip cache, no matrix — carry forward from Phase 13
- `softprops/action-gh-release@v2` with `generate_release_notes: true` — confirmed from charlesangus/anchors reference

### Integration Points
- New file: `.github/workflows/release.yml`
- Plugin `.py` files at repo root (7 files): `node_layout.py`, `node_layout_state.py`, `util.py`, `node_layout_prefs.py`, `node_layout_prefs_dialog.py`, `menu.py`, `make_room.py`
- `README.md` and `LICENSE` also at repo root

</code_context>

<specifics>
## Specific Ideas

- Follow charlesangus/anchors `release.yml` as the reference pattern — same structure, same action (`softprops/action-gh-release@v2`), same ZIP-folder approach
- anchors creates `anchors/` dir, copies files, zips it — node_layout does the same with `node_layout/`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 14-release-workflow*
*Context gathered: 2026-03-17*
