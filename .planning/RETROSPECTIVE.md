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

## Cross-Milestone Trends

| Milestone | Phases | Plans | Days | Notable |
|-----------|--------|-------|------|---------|
| v1.0 | 5 | 13 | 2 | First milestone; established all core patterns |
| v1.1 | 9 (incl. 3 inserted) | 30 | 12 | Full layout engine; 3 post-ship geometry bug phases; 276 tests |
