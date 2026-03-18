# Phase 13: Tooling + CI - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Add `pyproject.toml` with Ruff configuration and a GitHub Actions CI workflow that runs pytest and Ruff linting on every push and PR. No release workflow (Phase 14). No formatting enforcement beyond linting — Ruff is linter only here.

</domain>

<decisions>
## Implementation Decisions

### Python version
- Target Python 3.11 — matches Nuke 16 bundled Python
- Single version (no matrix) — keep CI fast and simple

### Ruff configuration
- Line length: 100
- Rule sets: E, F, W, B, I, SIM (as specified in TOOL-01)
- No per-file exceptions — menu.py long lines will be wrapped instead (see menu.py section)

### menu.py line wrapping
- All long `addCommand()` calls that exceed 100 chars must be wrapped to multi-line style with trailing comma
- Use the pattern already present at the bottom of menu.py for the Preferences entry:
  ```python
  layout_menu.addCommand(
      'Command Name',
      node_layout.function_name,
  )
  ```
- No E501 exemption — wrap the lines so they pass cleanly

### CI workflow structure
- Trigger: all branches on push + all pull requests
- One job: lint (Ruff) then test (pytest) sequentially — fail-fast on lint failure
- No separate parallel jobs

### CI reporting
- Standard GitHub Actions status checks — green/red check on PRs automatically

### Claude's Discretion
- Exact GitHub Actions `ubuntu-version` runner tag
- Whether to cache pip dependencies (reasonable to add for speed)
- pytest flags (e.g., `-v` verbosity)
- Ruff version pinning strategy in workflow

</decisions>

<specifics>
## Specific Ideas

- The Ruff wrapping style for menu.py should match the existing `Node Layout Preferences…` entry at the bottom of `menu.py` — that's already the canonical pattern in the file

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/` directory: all 276+ pytest tests already pass locally; no conftest changes expected
- `menu.py`: 7 lines over 100 chars, all `addCommand()` calls — each needs multi-line wrapping

### Established Patterns
- No existing `pyproject.toml`, `.github/`, or CI configuration — everything is net new
- Python source files: `node_layout.py`, `node_layout_state.py`, `util.py`, `node_layout_prefs.py`, `node_layout_prefs_dialog.py`, `menu.py`, `make_room.py`
- Tests live in `tests/` directory

### Integration Points
- `pyproject.toml` at repo root — Ruff config lives under `[tool.ruff]`
- `.github/workflows/ci.yml` — new file, no existing workflows to integrate with

### Blocker Note
- STATE.md flags: "Sibling project charlesangus/anchors has the reference CI/CD pattern — inspect before writing workflows" — researcher should check this for workflow structure reference

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 13-tooling-ci*
*Context gathered: 2026-03-17*
