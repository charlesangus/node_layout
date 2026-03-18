# Phase 13: Tooling + CI - Research

**Researched:** 2026-03-17
**Domain:** Python tooling (Ruff) + GitHub Actions CI
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Python version:** Target Python 3.11 — matches Nuke 16 bundled Python. Single version (no matrix).
- **Ruff line length:** 100
- **Ruff rule sets:** E, F, W, B, I, SIM (as specified in TOOL-01)
- **No per-file exceptions:** menu.py long lines will be wrapped instead
- **menu.py wrapping pattern:** All long `addCommand()` calls wrapped to multi-line style with trailing comma, matching the existing `Node Layout Preferences…` entry pattern
- **CI trigger:** All branches on push + all pull requests
- **CI structure:** One job — lint (Ruff) then test (pytest) sequentially; fail-fast on lint failure
- **No separate parallel jobs**
- **CI reporting:** Standard GitHub Actions status checks (green/red on PRs automatically)

### Claude's Discretion
- Exact GitHub Actions `ubuntu-version` runner tag
- Whether to cache pip dependencies (reasonable to add for speed)
- pytest flags (e.g., `-v` verbosity)
- Ruff version pinning strategy in workflow

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TOOL-01 | `pyproject.toml` with Ruff configuration (line length 100, E/F/W/B/I/SIM rules, no per-file exceptions) | Ruff `[tool.ruff]` + `[tool.ruff.lint]` structure confirmed; sibling project `charlesangus/anchors` is exact reference |
| CI-01 | GitHub Actions CI workflow runs pytest on every push and PR | Workflow trigger pattern + `actions/setup-python@v5` + `pip install pytest` confirmed from sibling project |
| CI-02 | GitHub Actions CI workflow runs Ruff linting on every push and PR | `pip install ruff` then `ruff check .` in workflow confirmed |
| CI-03 | CI workflow reports pass/fail status on PRs | Standard GitHub Actions behavior — any non-zero exit code causes red check; no extra config needed |
</phase_requirements>

---

## Summary

Phase 13 introduces two pieces of infrastructure: a `pyproject.toml` with Ruff linting configuration, and a `.github/workflows/ci.yml` GitHub Actions workflow. Both are net-new files (no existing CI configuration exists). The project already has 280 pytest tests that pass locally. The sibling project `charlesangus/anchors` (same author, same style) provides a battle-tested reference for both the pyproject.toml Ruff config and the GitHub Actions structure.

The most significant non-obvious work in this phase is **fixing hardcoded `/workspace/` paths in 14 test files**. These tests use `/workspace/node_layout.py` etc. as absolute paths, which works locally but will fail on GitHub Actions runners where the checkout path is `/home/runner/work/node_layout/node_layout/`. Without this fix, CI-01 will be broken despite all tests passing locally. The fix pattern already exists in several test files (`os.path.dirname(__file__)` relative paths) — it just needs to be applied consistently.

**Primary recommendation:** Use `ubuntu-24.04` runner (now `ubuntu-latest`), `actions/setup-python@v5` with Python 3.11, pip caching via `cache: 'pip'`, sequential lint-then-test job, and fix all 14 test files' hardcoded paths before pushing CI configuration.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ruff | >=0.10.0 (latest ~0.10.x) | Python linter enforcing E/F/W/B/I/SIM rules | Replaces flake8+isort+bugbear in one fast tool; project owner uses it in sibling repo |
| pytest | existing (already installed) | Test runner for 280 tests | Already the project's test framework |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| actions/checkout | v4 | Checkout repo in CI | Standard for all GitHub Actions workflows |
| actions/setup-python | v5 | Install Python 3.11 on runner | Standard Python setup action |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ruff | flake8 + isort + flake8-bugbear | Ruff is locked decision; flake8 is much slower and requires multiple tools |
| sequential lint+test | parallel jobs | Parallel adds complexity; sequential fail-fast on lint is locked decision |

**Installation (CI workflow):**
```bash
pip install ruff pytest
```

**Installation (local dev):**
```bash
pip install ruff
```

---

## Architecture Patterns

### Files to Create
```
.github/
└── workflows/
    └── ci.yml               # CI workflow (lint + test on push/PR)
pyproject.toml               # Ruff configuration at repo root
```

### Files to Modify
```
menu.py                      # 7 lines need wrapping to pass Ruff E501 at 100 chars
tests/
├── test_diamond_dot_centering.py   # hardcoded /workspace/ path
├── test_dot_font_scale.py          # hardcoded /workspace/ path
├── test_fan_alignment.py           # hardcoded /workspace/ path
├── test_group_context.py           # hardcoded /workspace/ path
├── test_horizontal_layout.py       # hardcoded /workspace/ path (multiple)
├── test_horizontal_margin.py       # hardcoded /workspace/ path
├── test_make_room_bug01.py         # hardcoded /workspace/ path
├── test_node_layout_bug02.py       # hardcoded /workspace/ path
├── test_node_layout_prefs.py       # hardcoded /workspace/ path
├── test_node_layout_prefs_dialog.py # hardcoded /workspace/ path
├── test_prefs_integration.py       # hardcoded /workspace/ path
├── test_scale_nodes.py             # hardcoded /workspace/ path
├── test_scale_nodes_axis.py        # hardcoded /workspace/ path
└── test_undo_wrapping.py           # hardcoded /workspace/ path
```

### Pattern 1: pyproject.toml Ruff Configuration
**What:** Single TOML file at repo root with `[tool.ruff]` for global settings and `[tool.ruff.lint]` for rule selection.
**When to use:** Always — this is the standard config location for Ruff.

```toml
# Source: charlesangus/anchors pyproject.toml (verified) + docs.astral.sh/ruff/configuration/
[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "B", "I", "SIM"]
```

Note: `SIM` is the flake8-simplify rule set. No `C90` (mccabe complexity) — anchors includes it but TOOL-01 does not require it.

### Pattern 2: GitHub Actions CI Workflow
**What:** Single-job workflow that installs Python 3.11, installs ruff+pytest, runs ruff check, then pytest.
**When to use:** Standard CI for Python projects without complex dependencies.

```yaml
# Source: charlesangus/anchors release.yml (adapted) + github.blog/changelog/2024-09-25
name: CI

on:
  push:
    branches: ["**"]
  pull_request:
    branches: ["**"]

jobs:
  lint-and-test:
    runs-on: ubuntu-24.04

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install ruff pytest

      - name: Lint with Ruff
        run: ruff check .

      - name: Run tests
        run: pytest tests/ -v
```

### Pattern 3: menu.py Multi-line addCommand() Wrapping
**What:** Convert single-line `addCommand()` calls exceeding 100 chars to multi-line form.
**When to use:** For all 7 lines in menu.py currently over 100 characters.

```python
# BEFORE (116 chars — fails E501):
layout_menu.addCommand('Layout Selected Horizontal (Place Only)', node_layout.layout_selected_horizontal_place_only)

# AFTER — matches existing Preferences entry pattern:
layout_menu.addCommand(
    'Layout Selected Horizontal (Place Only)',
    node_layout.layout_selected_horizontal_place_only,
)
```

For `addCommand()` calls that use string expressions (not function references):
```python
# BEFORE (124 chars):
layout_menu.addCommand("Select Upstream Ignoring Hidden", "util.select_upstream_ignoring_hidden()", "E", shortcutContext=2,)

# AFTER:
layout_menu.addCommand(
    "Select Upstream Ignoring Hidden",
    "util.select_upstream_ignoring_hidden()",
    "E",
    shortcutContext=2,
)
```

### Pattern 4: Test File Path Fix
**What:** Replace hardcoded `/workspace/` absolute paths with `__file__`-relative paths.
**When to use:** All 14 test files with hardcoded paths.

```python
# BEFORE (breaks on GitHub Actions):
NODE_LAYOUT_PATH = "/workspace/node_layout.py"

# AFTER (portable — already used in test_center_x.py and others):
import os
NODE_LAYOUT_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")
```

### Anti-Patterns to Avoid
- **`on: push: branches: [main]`:** Locks CI to one branch only — CONTEXT requires all branches
- **`ubuntu-latest` without explicit version:** Works but less reproducible; `ubuntu-24.04` is explicit and is currently what `ubuntu-latest` resolves to
- **`pip install ruff` without version pin:** Acceptable for this project (CONTEXT says pinning strategy is at discretion); unpinned means always-latest Ruff which occasionally changes behavior
- **Separate lint and test jobs:** CONTEXT decision locks to single sequential job
- **`per-file-ignores` for menu.py:** CONTEXT decision locks to wrapping instead of exempting

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Import sorting | Custom sort scripts | Ruff `I` rules | Ruff enforces isort-compatible sorting automatically |
| Line length checking | Manual awk scripts | Ruff `E501` (included in `E`) | Integrated into Ruff check pass |
| Python setup in CI | Custom shell scripts | `actions/setup-python@v5` | Handles PATH, pip, caching automatically |
| PR status checks | Custom GitHub API calls | GitHub Actions built-in | Any failing step = red check automatically |
| Pip dependency caching | Custom cache key scripts | `setup-python cache: 'pip'` | Built-in support reads pyproject.toml hash automatically |

**Key insight:** GitHub Actions' status check integration is automatic — there is no API call or extra step needed. Any job step that exits non-zero marks the commit/PR as failed. No `actions/github-script` or similar is needed for CI-03.

---

## Common Pitfalls

### Pitfall 1: Hardcoded `/workspace/` Paths in Tests
**What goes wrong:** All 14 test files define paths like `NODE_LAYOUT_PATH = "/workspace/node_layout.py"`. On GitHub Actions, the checkout path is `/home/runner/work/node_layout/node_layout/`. Every test that opens these paths will fail with `FileNotFoundError`.
**Why it happens:** Tests were written and run exclusively in the `/workspace/` Docker environment.
**How to avoid:** Replace all hardcoded paths with `os.path.join(os.path.dirname(__file__), "..", "filename.py")`. This pattern is already used in `test_center_x.py`, `test_state_integration.py`, and `test_margin_symmetry.py` — it is the established correct pattern.
**Warning signs:** If CI shows `FileNotFoundError` or `ModuleNotFoundError` on tests that pass locally.

### Pitfall 2: Ruff `[tool.ruff.lint]` vs `[tool.ruff]` Key Placement
**What goes wrong:** In Ruff >=0.2.0, `select` must be under `[tool.ruff.lint]`, not `[tool.ruff]`. Older tutorials show `[tool.ruff]` with `select` directly — this raises a deprecation error or is silently ignored.
**Why it happens:** Ruff restructured its config schema; `select` moved to the `lint` sub-table.
**How to avoid:** Always use `[tool.ruff.lint]` for `select`, `ignore`, and `per-file-ignores`. Use `[tool.ruff]` only for `line-length` and other global settings.
**Warning signs:** Ruff warning "The `select` option is no longer supported in `[tool.ruff]`".

### Pitfall 3: Ruff Checks `menu.py` Imports Too
**What goes wrong:** `menu.py` imports `nuke`, `node_layout`, etc. Ruff's `F401` (unused imports) will not fire because all imports are used, but `E501` will fire on the long lines until they are wrapped.
**Why it happens:** menu.py has 7 lines over 100 chars, all `addCommand()` calls.
**How to avoid:** Wrap all 7 lines before or as part of the same wave that adds pyproject.toml, so `ruff check .` passes on first run.
**Warning signs:** `ruff check .` exits non-zero before the CI workflow runs any tests.

### Pitfall 4: Other Source Files May Have Ruff Violations
**What goes wrong:** Running `ruff check .` for the first time on the full codebase may reveal violations in `node_layout.py`, `util.py`, etc. beyond just menu.py.
**Why it happens:** No prior linting enforcement; code was written without Ruff.
**How to avoid:** Run `ruff check .` locally after adding `pyproject.toml` and fix all violations before committing. Do not commit `pyproject.toml` and `ci.yml` together until `ruff check .` exits 0 locally.
**Warning signs:** CI immediately fails on first push with lint errors in non-menu.py files.

### Pitfall 5: `cache: 'pip'` Requires a Dependency File
**What goes wrong:** `actions/setup-python` with `cache: 'pip'` looks for `requirements.txt` or `pyproject.toml` to generate the cache key. If neither declares ruff/pytest as dependencies, the cache key is unstable.
**Why it happens:** We install ruff+pytest inline (`pip install ruff pytest`) without a requirements file.
**How to avoid:** Either add a minimal `requirements-dev.txt` with `ruff` and `pytest`, or skip pip caching (just omit `cache: 'pip'`). For a two-package install, caching saves <10 seconds — skipping is acceptable. Alternatively, `pyproject.toml` can declare `[project.optional-dependencies]` for dev deps.
**Warning signs:** Cache restore misses every run despite `cache: 'pip'` being set.

---

## Code Examples

Verified patterns from sibling project and official sources:

### Complete pyproject.toml
```toml
# Source: charlesangus/anchors pyproject.toml (verified 2026-03-17)
# Adapted: removed C90 (not in TOOL-01), removed per-file-ignores (not in TOOL-01)
[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "B", "I", "SIM"]
```

### Complete ci.yml
```yaml
# Source: charlesangus/anchors release.yml (structure) + GitHub Actions docs
name: CI

on:
  push:
    branches: ["**"]
  pull_request:
    branches: ["**"]

jobs:
  lint-and-test:
    runs-on: ubuntu-24.04

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install ruff pytest

      - name: Lint with Ruff
        run: ruff check .

      - name: Run tests
        run: pytest tests/ -v
```

### Portable Test Path Resolution
```python
# Source: test_center_x.py (existing pattern in this codebase)
import os
NODE_LAYOUT_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")
NODE_LAYOUT_PREFS_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout_prefs.py")
NODE_LAYOUT_STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout_state.py")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| flake8 + isort + flake8-bugbear | ruff (single tool) | ~2023 | 10-100x faster, one config block |
| `ubuntu-latest` = Ubuntu 22.04 | `ubuntu-latest` = Ubuntu 24.04 | Jan 2025 | Python 3.11 available without extra setup |
| `[tool.ruff] select = [...]` | `[tool.ruff.lint] select = [...]` | Ruff 0.2.0 (2024) | Old placement is deprecated/ignored |

**Deprecated/outdated:**
- `ubuntu-20.04` runner: Removed/brownout started March 2025 — do not use
- `[tool.ruff] select`: Moved to `[tool.ruff.lint]` as of Ruff 0.2.0

---

## Open Questions

1. **Ruff violations in non-menu.py source files**
   - What we know: No prior linting enforcement; code quality is unknown
   - What's unclear: How many and what kind of violations exist in `node_layout.py`, `util.py`, `make_room.py`, etc.
   - Recommendation: Dry-run `ruff check .` locally as Wave 0/Task 1 before writing workflow; treat fixing violations as part of the pyproject.toml task

2. **Ruff version pinning**
   - What we know: CONTEXT says pinning strategy is at Claude's discretion; sibling repo does not pin (`pip install ruff`)
   - What's unclear: Whether `SIM` rule behavior across Ruff versions could cause unexpected failures
   - Recommendation: Match sibling project — unpin for now, pin if a future Ruff update breaks CI

3. **`cache: 'pip'` inclusion**
   - What we know: Only ruff+pytest are installed; install takes ~5 seconds unpinned
   - What's unclear: Whether the cache overhead is worth it for a two-package install
   - Recommendation: Omit `cache: 'pip'` initially (simpler); add if CI run time becomes a concern

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (version detected from environment) |
| Config file | none — see Wave 0 (can add `[tool.pytest.ini_options]` to pyproject.toml if needed) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TOOL-01 | `pyproject.toml` exists with correct Ruff config | smoke | `python -c "import tomllib; c=tomllib.load(open('pyproject.toml','rb')); assert c['tool']['ruff']['line-length']==100"` | ❌ Wave 0 |
| CI-01 | CI workflow runs pytest on push/PR | manual-only | N/A — requires GitHub push to verify | N/A |
| CI-02 | CI workflow runs Ruff on push/PR | manual-only | N/A — requires GitHub push to verify | N/A |
| CI-03 | PR shows green/red check | manual-only | N/A — requires GitHub PR to verify | N/A |
| (prerequisite) | All 280 tests pass with portable paths | unit | `pytest tests/ -v` | ✅ (after path fix) |
| (prerequisite) | `ruff check .` exits 0 | smoke | `ruff check .` | ❌ Wave 0 (after pyproject.toml) |

Note: CI-01, CI-02, and CI-03 can only be verified by pushing to GitHub and observing the Actions tab. Local verification is: (a) tests pass with `pytest tests/ -v`, (b) linting passes with `ruff check .`, (c) workflow YAML is syntactically valid.

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v` + `ruff check .`
- **Phase gate:** Full suite green + `ruff check .` clean + push to GitHub and confirm green check

### Wave 0 Gaps
- [ ] `pyproject.toml` must exist before `ruff check .` can run
- [ ] All 14 test files with `/workspace/` paths must be fixed before `pytest tests/ -v` passes on CI
- [ ] Framework already installed locally; CI installs via `pip install pytest`

---

## Sources

### Primary (HIGH confidence)
- `charlesangus/anchors` GitHub repo — pyproject.toml and release.yml inspected directly via `gh api` on 2026-03-17
- Workspace source inspection — `/workspace/menu.py` (7 long lines confirmed), `/workspace/tests/*.py` (14 files with hardcoded paths confirmed), test count: 280 test functions confirmed

### Secondary (MEDIUM confidence)
- [Ruff configuration docs](https://docs.astral.sh/ruff/configuration/) — `[tool.ruff.lint]` section placement confirmed via web search + sibling project cross-reference
- [GitHub Actions ubuntu-latest = ubuntu-24.04](https://github.blog/changelog/2024-09-25-actions-new-images-and-ubuntu-latest-changes/) — migration completed January 2025 confirmed
- [actions/setup-python](https://github.com/actions/setup-python) — `cache: 'pip'` support confirmed via web search

### Tertiary (LOW confidence)
- Ruff version 0.10.x as "current" — based on web search result mentioning Ruff v0.10.0 released March 13, 2025; exact latest version not pinned in this research

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — sibling project provides exact reference, confirmed by inspection
- Architecture: HIGH — files to create and modify confirmed by direct workspace inspection
- Pitfalls: HIGH (path fix) / MEDIUM (other source file violations) — path issue confirmed by inspection; violation count in other files is unknown

**Research date:** 2026-03-17
**Valid until:** 2026-09-17 (stable tooling; Ruff config schema changes infrequently)
