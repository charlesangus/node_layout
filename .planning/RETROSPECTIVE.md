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

## Cross-Milestone Trends

| Milestone | Phases | Plans | Days | Notable |
|-----------|--------|-------|------|---------|
| v1.0 | 5 | 13 | 2 | First milestone; established all core patterns |
