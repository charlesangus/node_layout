# Phase 14: Release Workflow - Research

**Researched:** 2026-03-17
**Domain:** GitHub Actions release workflow (tag-triggered, ZIP artifact, GitHub Release)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**CI gate strategy**
- Two separate jobs: `test` job runs Ruff + pytest; `build` job has `needs: test`
- `build` job only runs if `test` passes — REL-02 gating enforced
- Same runner and Python version as CI: ubuntu-24.04, Python 3.11
- Ruff + pytest both required in `test` job (not pytest-only like anchors)

**ZIP structure**
- Create a `node_layout/` directory, copy files into it, then ZIP that folder
- Contents: `node_layout.py`, `node_layout_state.py`, `util.py`, `node_layout_prefs.py`, `node_layout_prefs_dialog.py`, `menu.py`, `make_room.py`, `README.md`, `LICENSE`
- File list is hardcoded (not a glob) — no accidental inclusion of future non-plugin files
- Tests excluded — ZIP is user-facing distribution only
- ZIP named `node_layout-${GITHUB_REF_NAME}.zip` (keeps `v` prefix, e.g. `node_layout-v1.2.zip`)
- Install path intent: user drops `node_layout/` into `~/.nuke/` and adds `nuke.pluginAddPath('node_layout')` to init.py

**Release notes**
- `generate_release_notes: true` via softprops/action-gh-release@v2
- GitHub auto-generates from commits/PRs since last tag — no manual authoring required

**Publish behavior**
- Release published immediately when workflow completes — no draft step
- `permissions: contents: write` required on the workflow

### Claude's Discretion
- Exact pip install command (whether to pin ruff/pytest versions)
- Release name format (tag name vs. custom string)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REL-01 | Release workflow triggers on `v*` git tag push | `on: push: tags: ["v*"]` trigger pattern in GitHub Actions |
| REL-02 | Release workflow gates on passing tests and linting before building artifact | Two-job structure with `needs: test` on `build` job |
| REL-03 | Release workflow produces a versioned ZIP (`node_layout-vX.Y.zip`) containing all plugin `.py` files, `README.md`, and `LICENSE` | Shell `mkdir`/`cp`/`zip` commands in `build` job steps |
| REL-04 | Release workflow publishes a GitHub Release with the ZIP attached and auto-generated release notes | `softprops/action-gh-release@v2` with `files:` and `generate_release_notes: true` |
</phase_requirements>

---

## Summary

Phase 14 requires exactly one new file: `.github/workflows/release.yml`. All decisions are locked in CONTEXT.md. The workflow is a straightforward two-job GitHub Actions file — `test` mirrors the existing `ci.yml` job, and `build` gates on it, creates a staging directory, copies hardcoded files, zips them, and publishes via `softprops/action-gh-release@v2`.

The existing `ci.yml` (ubuntu-24.04, Python 3.11, `pip install ruff pytest`, `ruff check .`, `pytest tests/ -v`) is the template for the `test` job verbatim. The `build` job adds only the ZIP construction and release publish steps. No changes to any existing files are required.

The only discretionary decisions are: whether to pin ruff/pytest versions in `pip install` (recommendation: don't pin — consistent with ci.yml), and the release name format (recommendation: use the tag name directly via `${{ github.ref_name }}`).

**Primary recommendation:** Write `release.yml` as a direct adaptation of `ci.yml` with a second `build` job. One file, no other changes.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| actions/checkout | v4 | Checkout repo in both jobs | Same as ci.yml |
| actions/setup-python | v5 | Python 3.11 environment | Same as ci.yml |
| softprops/action-gh-release | v2 | Publish GitHub Release with files | Confirmed in CONTEXT.md; current version is v2 (maps to latest v2.x tag) |

**Version note:** `softprops/action-gh-release@v2` is a floating major-version tag that tracks the latest v2 release (currently 2.6.1 as of 2026-03-17, verified via npm registry). Using `@v2` is the standard pattern for this action and matches the charlesangus/anchors reference.

**No additional packages.** The `build` job uses only standard shell tools (`mkdir`, `cp`, `zip`) available on ubuntu-24.04 — no extra installs needed.

### ZIP construction (shell, no library needed)

```bash
mkdir node_layout
cp node_layout.py node_layout_state.py util.py \
   node_layout_prefs.py node_layout_prefs_dialog.py \
   menu.py make_room.py README.md LICENSE node_layout/
zip -r node_layout-${GITHUB_REF_NAME}.zip node_layout/
```

`zip` is pre-installed on ubuntu-24.04 — no `apt-get install` step required.

## Architecture Patterns

### Recommended Project Structure

```
.github/
└── workflows/
    ├── ci.yml           # Existing — unchanged
    └── release.yml      # New — this phase
```

### Pattern: Two-Job Tag-Triggered Workflow

**What:** Separate `test` and `build` jobs where `build` declares `needs: test`. GitHub will not start `build` until `test` completes with success.

**When to use:** Any time artifact creation must be gated on quality checks — prevents publishing broken releases.

**Trigger:**
```yaml
on:
  push:
    tags:
      - "v*"
```

**Job dependency:**
```yaml
jobs:
  test:
    runs-on: ubuntu-24.04
    # ... mirror of ci.yml lint-and-test job

  build:
    runs-on: ubuntu-24.04
    needs: test
    permissions:
      contents: write
    # ... ZIP + release steps
```

### Pattern: `GITHUB_REF_NAME` for Tag-Derived Names

When triggered by a tag push, `github.ref_name` (or `$GITHUB_REF_NAME` in shell) resolves to the tag name itself (e.g., `v1.2`). This is the correct variable to use for the ZIP filename and release name.

```yaml
- name: Build ZIP
  run: |
    mkdir node_layout
    cp node_layout.py node_layout_state.py util.py \
       node_layout_prefs.py node_layout_prefs_dialog.py \
       menu.py make_room.py README.md LICENSE node_layout/
    zip -r node_layout-${{ github.ref_name }}.zip node_layout/
```

### Pattern: softprops/action-gh-release@v2

```yaml
- name: Publish Release
  uses: softprops/action-gh-release@v2
  with:
    files: node_layout-${{ github.ref_name }}.zip
    generate_release_notes: true
```

`generate_release_notes: true` instructs GitHub to auto-generate release notes from commits/PRs since the previous tag. No `body:` or `body_file:` needed.

### Release name format (Claude's discretion)

**Recommendation:** Omit `name:` from the release step entirely. When `name` is not specified, `softprops/action-gh-release@v2` defaults to the tag name (e.g., `v1.2`). This is clean and requires no additional templating.

Alternatively, a custom string like `name: node_layout ${{ github.ref_name }}` is equally valid. Either works; the simpler omission is preferred.

### pip install command (Claude's discretion)

**Recommendation:** Use `pip install ruff pytest` without version pins — identical to ci.yml. Pinning would create a maintenance burden and diverge from the CI pattern without benefit for a release gate.

### Anti-Patterns to Avoid

- **Glob-based file collection in ZIP:** `cp *.py node_layout/` would accidentally include test runner shims or future non-plugin Python files. Use the hardcoded list.
- **Single combined job:** Running lint/test and ZIP/release in one job means the artifact exists in workspace even if tests fail (requires explicit early-exit logic). Two jobs with `needs:` is cleaner and idiomatic.
- **Missing `permissions: contents: write`:** Without this, `softprops/action-gh-release` will fail with a 403. This permission must be on the `build` job (or at workflow level).
- **Using `GITHUB_REF` instead of `GITHUB_REF_NAME`:** `GITHUB_REF` returns `refs/tags/v1.2`; `GITHUB_REF_NAME` returns `v1.2`. Use `GITHUB_REF_NAME` (or `github.ref_name` in expressions).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GitHub Release creation | Custom API calls via `curl`/`gh` | `softprops/action-gh-release@v2` | Handles upload URL, multipart asset upload, retry, rate limiting |
| Release note generation | Custom commit log scripting | `generate_release_notes: true` | GitHub generates from PR titles and commits automatically |

**Key insight:** `softprops/action-gh-release@v2` handles the entire GitHub Releases API surface. The ZIP itself is simple shell — that part genuinely does not need a library.

## Common Pitfalls

### Pitfall 1: `permissions: contents: write` placement

**What goes wrong:** Workflow fails with HTTP 403 when trying to create the release.
**Why it happens:** GitHub Actions defaults to `contents: read`. Write permission must be explicitly granted for any job that creates releases or pushes tags.
**How to avoid:** Place `permissions: contents: write` on the `build` job (not the `test` job, which doesn't write). Alternatively set it at workflow level — but job-level is more conservative.
**Warning signs:** Error message "Resource not accessible by integration" or HTTP 403 in action logs.

### Pitfall 2: ZIP working directory

**What goes wrong:** ZIP contains full path like `./node_layout/node_layout.py` or just flat files with no directory.
**Why it happens:** Where `zip` is run from determines the paths inside the archive.
**How to avoid:** Run `zip -r node_layout-v1.2.zip node_layout/` from the repo root (default `$GITHUB_WORKSPACE`). This produces `node_layout/node_layout.py` inside the archive — the correct install path.
**Warning signs:** Users report having to manually restructure after download.

### Pitfall 3: Tag not checked out

**What goes wrong:** `actions/checkout@v4` by default checks out the ref that triggered the workflow. For tag pushes this is the tagged commit — this is correct behavior and requires no special configuration.
**Why it happens:** Developers sometimes add `ref:` overrides unnecessarily.
**How to avoid:** Do not add a `ref:` input to checkout in the `build` job. The default is correct.

### Pitfall 4: `generate_release_notes` requires no previous release for first tag

**What goes wrong:** First release has empty auto-generated notes.
**Why it happens:** GitHub generates notes from commits since the previous tag. With no previous tag, GitHub uses the beginning of history — notes will be generated but may be long.
**How to avoid:** This is expected behavior for the first release. No action needed.

## Code Examples

### Complete release.yml

```yaml
# Source: pattern from ci.yml + softprops/action-gh-release@v2 docs
name: Release

on:
  push:
    tags:
      - "v*"

jobs:
  test:
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

  build:
    runs-on: ubuntu-24.04
    needs: test
    permissions:
      contents: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Build ZIP
        run: |
          mkdir node_layout
          cp node_layout.py node_layout_state.py util.py \
             node_layout_prefs.py node_layout_prefs_dialog.py \
             menu.py make_room.py README.md LICENSE node_layout/
          zip -r node_layout-${{ github.ref_name }}.zip node_layout/

      - name: Publish Release
        uses: softprops/action-gh-release@v2
        with:
          files: node_layout-${{ github.ref_name }}.zip
          generate_release_notes: true
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `actions/create-release` + `actions/upload-release-asset` (two actions) | `softprops/action-gh-release@v2` (one action) | ~2021 | Simpler workflow, combined create+upload |
| Manual release notes in `body:` | `generate_release_notes: true` | GitHub feature ~2021 | Zero maintenance, auto-populated from PRs/commits |
| `softprops/action-gh-release@v1` | `@v2` | 2023 | v2 uses Node 20, v1 is deprecated |

**Deprecated/outdated:**
- `actions/create-release`: Deprecated by GitHub; do not use
- `softprops/action-gh-release@v1`: Uses Node 16 (deprecated); use `@v2`

## Open Questions

None — all decisions are locked in CONTEXT.md. The implementation is fully specified.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (no version pinned) |
| Config file | `pyproject.toml` (Ruff config only; pytest uses default discovery) |
| Quick run command | `pytest tests/ -v` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REL-01 | Workflow file exists with correct trigger | manual | Inspect `.github/workflows/release.yml` trigger block | ❌ Wave 0 |
| REL-02 | `build` job has `needs: test` | manual | Inspect workflow YAML for `needs: test` on build job | ❌ Wave 0 |
| REL-03 | ZIP contains correct files with `node_layout/` prefix | manual | Push a `v*` tag to GitHub and inspect release asset | ❌ Wave 0 |
| REL-04 | GitHub Release published with ZIP and auto-notes | manual | Inspect GitHub Releases page after tag push | ❌ Wave 0 |

**Note:** All REL requirements are verified by workflow file content inspection and a live tag push smoke test. There are no unit tests for a GitHub Actions workflow file itself — correctness is verified by reading the YAML and by the end-to-end smoke test.

### Sampling Rate

- **Per task commit:** Inspect `release.yml` YAML structure manually
- **Per wave merge:** N/A — single-plan phase
- **Phase gate:** End-to-end smoke test (push a `v*` tag, verify release appears on GitHub) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `.github/workflows/release.yml` — the only deliverable; does not exist yet

*(No test files needed — workflow validation is structural inspection + live smoke test)*

## Sources

### Primary (HIGH confidence)

- Existing `/workspace/.github/workflows/ci.yml` — verbatim template for `test` job
- CONTEXT.md locked decisions — all architectural choices pre-decided
- npm registry: `softprops/action-gh-release` version 2.6.1 confirmed current as of 2026-03-17

### Secondary (MEDIUM confidence)

- GitHub Actions documentation pattern for `on: push: tags:` trigger — standard, widely documented
- `softprops/action-gh-release@v2` README — `generate_release_notes`, `files`, `permissions` behavior

### Tertiary (LOW confidence)

None — no unverified claims in this research.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — actions are verified (ci.yml + npm registry check)
- Architecture: HIGH — fully specified in CONTEXT.md, no exploration required
- Pitfalls: HIGH — `permissions: contents: write` and `GITHUB_REF_NAME` are well-known GitHub Actions specifics

**Research date:** 2026-03-17
**Valid until:** 2026-06-17 (stable — GitHub Actions major versions change slowly)
