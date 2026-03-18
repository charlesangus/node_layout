# Retrospective

## Milestone: v1.0 — Quality & Preferences

**Shipped:** 2026-03-05
**Phases:** 5 | **Plans:** 13

### What Was Built

- Phase 1: Per-operation caches (toolbar map, color lookups), diamond Dot custom knob tagging, narrowed exception handling
- Phase 2: Fixed 5 layout bugs — make_room() init, stale node filter refs, input-0 centering, margin symmetry, diamond Dot post-placement centering
- Phase 3: Undo group wrapping for both layout commands — Ctrl+Z atomically restores all nodes
- Phase 4: JSON-backed NodeLayoutPrefs singleton, PySide6 dialog, sqrt-scaled subtree margins threading through full pipeline
- Phase 5: 7 new menu commands (compact/loose layout, shrink/expand selected/upstream), scheme_multiplier pipeline, horizontal/vertical margin split

### What Worked

- **AST-based tests for Nuke code**: Writing tests against ast.parse() allowed verifying structural properties without a Nuke license. Caught real issues before manual testing.
- **Plan-then-implement discipline**: Each plan clearly stated what must be TRUE as success criteria, which made verification straightforward.
- **Following Labelmaker pattern exactly**: Having a sibling plugin to copy eliminated all architecture decisions for the prefs system.
- **Fixing bugs in dependency order**: Fixing make_room() and node filter before tackling centering bugs meant each fix was isolated and clean.

### What Was Inefficient

- **Git object corruption**: A disk issue corrupted multiple git object files, requiring manual repair and recovery work mid-project. No work was lost but it cost session time.
- **Missing SUMMARY.md files**: Plans 01-01 and 04-01 never got SUMMARY.md files written, leaving gaps in the paper trail. The work was done but not documented.
- **scheme_multiplier scope creep**: Phase 5 grew from 2 plans to 4 plans as the horizontal/vertical margin split and scale function bugs were discovered during implementation.

### Patterns Established

- Per-operation cache reset: set module-level globals to None at each public entry point
- Custom knob tagging for programmatically-created nodes (reliable identification without relying on user-settable flags)
- try/except/else for Nuke undo groups — end() in else, cancel() in except
- scheme_multiplier resolves to normal_multiplier at the top call level, not recursively
- sqrt-scaled margin: int(base * multiplier * sqrt(n) / sqrt(ref)) — backward-compatible and proportional

### Key Lessons

- **Commit often**: The git corruption happened between commits, losing staged-but-uncommitted work. The `/gsd:complete-milestone` archival step should always be committed immediately.
- **SUMMARY.md before moving on**: Missing summaries for 01-01 and 04-01 only became apparent at milestone completion. Write them while the context is fresh.
- **Phase 5 scope**: "New commands" sounds simple but threading a new parameter through a recursive call chain touches many files. Budget extra plans for pipeline changes.

### Cost Observations

- Sessions: ~3 sessions over 2 days
- Notable: AST-based tests were a strong investment — they ran in CI without Nuke and caught real bugs

---

## Milestone: v1.1 — Layout Engine & State

**Shipped:** 2026-03-17
**Phases:** 9 (incl. 3 inserted: 11.1, 11.2, 12) | **Plans:** 30

### What Was Built

- Phase 6: Horizontal/mask gap prefs, default rebalance, Group context fix, scheme command renames
- Phase 7: node_layout_state.py module; hidden knobs on every touched node storing mode/scheme/scale; replay on re-layout
- Phase 8: _dot_font_scale() multiplier for subtree margins driven by Dot font size
- Phase 9: Fan alignment (_is_fan_active, fan branches in compute_dims and place_subtree, mask-left)
- Phase 10: Axis-specific H/V/Both scale commands; expand push-away
- Phase 11: place_subtree_horizontal(), _find_or_create_output_dot(), mode dispatch and replay
- Phase 11.1 (INSERTED): Fixed spine_x left-extent overlap bug and output Dot Y misalignment
- Phase 11.2 (INSERTED): Fixed chain clearance (place-then-measure-then-shift) and Phase 2 anchor clamping
- Phase 12 (INSERTED): Fixed fan Dot row Y, A1 X clearance, and compute_dims overhang width

### What Worked

- **Nuke-stub unit tests**: The stub pattern (`_StubKnob`, `_StubNode` injected via `sys.modules`) allowed thorough state-storage tests without Nuke. 276 tests ran in CI with no Nuke license.
- **RED scaffold first, GREEN second**: Every feature phase wrote failing tests in plan -01, then turned them green in plan -02. Minimal rework; the acceptance criteria were clear from the start.
- **Inserted decimal phases for bug fixes**: When horizontal geometry bugs surfaced post-ship, 11.1 and 11.2 cleanly contained the fixes without renumbering Phase 12 (fan fix). The decimal convention worked exactly as designed.
- **compute_dims memo key extension**: Extending the 4-tuple to a 5-tuple (adding layout_mode) was a clean, localized change that correctly invalidated cached dims when mode changed.

### What Was Inefficient

- **Multiple horizontal bug fix phases**: Phases 11.1, 11.2, and 12 were all post-ship corrections. The original Phase 11 UAT found the spine geometry issues, but the full scope (bbox clearance, Phase 2 anchor clamping, fan Dot Y) wasn't fully visible until integration testing. Better pre-ship integration testing could have collapsed some of this into Phase 11.
- **Nyquist VALIDATION.md metadata never updated**: All VALIDATION.md files were scaffolded and left in `status: draft`. The audit flagged this as tech debt. The actual test coverage is solid but the metadata trail is incomplete.
- **Phase 06 predates VALIDATION.md**: Phase 6 was created before the Nyquist validation workflow existed, so it has no VALIDATION.md at all. Minor; low priority.

### Patterns Established

- Nuke-stub injection pattern: `import sys; sys.modules['nuke'] = _StubNuke(); import module_under_test`
- State module: `read_node_state()` / `write_node_state()` / `clear_node_state()` in node_layout_state.py
- Compute_dims memo key: 5-tuple `(node_id, scheme_multiplier, h_scale, v_scale, layout_mode)`
- Decimal phase numbering for inserted work between phases
- Post-ship geometry bug workflow: RED regression tests → arithmetic fix → full regression run

### Key Lessons

- **Integration testing before shipping horizontal mode**: The spine geometry bugs (left-extent, Dot Y, bbox clearance) were discovered after shipping Phase 11. A pre-ship integration test covering the embedded-in-vertical-tree scenario would have caught these. Add integration tests to horizontal-mode UAT criteria.
- **VALIDATION.md metadata needs active maintenance**: The scaffold creates the file but the per-task tracking requires active updates during execution. Either update it as part of each plan's done-criteria or drop it — stale draft files create misleading audit results.
- **Fan + horizontal coexistence complexity**: The fan and horizontal paths each required 2 geometry bug fix phases. When two non-trivial layout paths are added in the same milestone, their interaction under real DAG shapes produces edge cases that are hard to anticipate from first principles. Budget extra phases for integration.

### Cost Observations

- Sessions: ~8 sessions over 12 days
- Notable: Nuke-stub tests were a strong investment — 276 tests, all passing in CI without Nuke, with zero false negatives on the geometry bugs that did slip through

---

## Milestone: v1.2 — CI/CD

**Shipped:** 2026-03-18
**Phases:** 2 (13–14) | **Plans:** 4

### What Was Built

- Phase 13: pyproject.toml with Ruff config; 14 test files migrated to `__file__`-relative paths; zero-violation Ruff compliance across 20 files; GitHub Actions CI workflow (Ruff + pytest on every push/PR)
- Phase 14: GitHub Actions release workflow — `v*` tag triggers test gate, builds `node_layout-vX.Y.zip` from 9 hardcoded files, publishes GitHub Release with auto-generated notes via softprops/action-gh-release@v2

### What Worked

- **Sequential lint-then-test single CI job**: Fast-fail on lint errors before running 280 tests avoids wasted compute and gives immediate feedback on style regressions.
- **Hardcoded file list for ZIP**: Explicit 9-file `cp` commands prevent accidental inclusion of future non-distribution files without requiring any glob maintenance.
- **Mirroring CI job verbatim in release workflow**: The `test` job in the release workflow is a direct copy of the CI job — same OS, Python version, packages. No divergence possible.
- **Ruff auto-fix first**: Running `ruff check . --fix` before manual E501 wrapping cleaned up import ordering and simple patterns automatically, leaving only structural wraps to do manually.

### What Was Inefficient

- **14 test files with hardcoded paths**: The `/workspace/` path problem was obvious in retrospect — any new test file added in this environment would inherit the same issue. A portable path pattern should have been established from the first test file. (Now established as a convention.)
- **Ruff violations discovered incrementally**: 140 E501 violations across 20 files needed manual wrapping. Most were from code written before Ruff was configured. The per-plan structure (configure first, then fix) was correct, but the volume was higher than anticipated.

### Patterns Established

- `__file__`-relative test imports: `sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))` for all test files
- CI pattern: single sequential `lint-and-test` job on ubuntu-24.04, Python 3.11, no pip cache
- Release pattern: two-job workflow (`test` + `build`) with `needs: test` gate; hardcoded file list; `github.ref_name` in artifact name
- Ruff config: `[tool.ruff.lint]` only in `pyproject.toml` (no `[project]` section); select = E/F/W/B/I/SIM

### Key Lessons

- **Portable paths from day one**: Establish `__file__`-relative imports in the first test file of a project, not retroactively. Adding a linting rule for hardcoded absolute paths would catch this automatically.
- **Two-job release workflow is the right default**: The `test` job gate prevents publishing broken artifacts — this pattern should be standard for any future release workflow.
- **Ruff compliance is cheapest at authorship**: Fixing 140 E501 violations retroactively was mechanical but time-consuming. Future phases should run `ruff check` incrementally as files are written.

### Cost Observations

- Sessions: 1 session over 1 day
- Notable: Fastest milestone so far — pure tooling with no layout algorithm changes. The test suite validated nothing broke.

---

## Cross-Milestone Trends

| Milestone | Phases | Plans | Days | Notable |
|-----------|--------|-------|------|---------|
| v1.0 | 5 | 13 | 2 | First milestone; established all core patterns |
| v1.1 | 9 (incl. 3 inserted) | 30 | 12 | Full layout engine; 3 post-ship geometry bug phases; 276 tests |
| v1.2 | 2 | 4 | 1 | Pure CI/CD tooling; fastest milestone; 49 files changed |
