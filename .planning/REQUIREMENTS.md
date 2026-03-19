# Requirements: node_layout

**Defined:** 2026-03-18
**Core Value:** Layout operations must be reliable, undoable, and configurable — users need to trust the tool won't silently misbehave.

## v1.3 Requirements

Requirements for the Freeze Layout milestone. Each maps to roadmap phases.

### Freeze Commands

- [x] **FRZE-01**: User can freeze selected nodes into a named group via "Freeze Selected" menu command (with keyboard shortcut)
- [x] **FRZE-02**: User can unfreeze selected nodes via "Unfreeze Selected" menu command (with keyboard shortcut)
- [x] **FRZE-03**: Freeze group UUID is stored as an invisible knob on the existing hidden layout tab; no visual indicator appears in the DAG

### Layout Integration

- [x] **FRZE-04**: Layout crawl runs a preprocessing step that detects all freeze groups before any node positioning begins (analogous to existing horizontal block detection)
- [x] **FRZE-05**: During preprocessing, nodes topologically inserted between frozen nodes in the DAG auto-join the freeze group (no real-time callbacks; resolved at crawl time only)
- [x] **FRZE-06**: Layout positions a frozen block as a unit — the root node (most downstream node in the block) is placed by the layout algorithm and all other block nodes are repositioned to maintain their original relative offsets
- [x] **FRZE-07**: Push-away (expand) treats a frozen block's bounding box as a single rigid obstacle; the entire block shifts as a unit when pushed

## Future Requirements

### Potential v1.4+

- Freeze group visualization (e.g. overlay or node tint) — explicitly deferred; no DAG clutter in v1.3
- Per-group freeze label / name — UUID is sufficient for v1.3 identity
- Freeze membership query command ("which group is this node in?") — defer until user need is established

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time auto-join callbacks | Nuke callback overhead and complexity; preprocessing at crawl time is sufficient |
| Visual freeze indicator in DAG | User prefers no DAG clutter; state is in hidden knobs |
| Nested freeze groups | Not needed; single-level grouping covers all intended use cases |
| Cross-script freeze state | Freeze groups are per-session layout artifacts; not intended to persist across script loads differently from other state |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FRZE-01 | Phase 15 | Complete |
| FRZE-02 | Phase 15 | Complete |
| FRZE-03 | Phase 15 | Complete |
| FRZE-04 | Phase 16 | Complete |
| FRZE-05 | Phase 16 | Complete |
| FRZE-06 | Phase 16 | Complete |
| FRZE-07 | Phase 16 | Complete |

**Coverage:**
- v1.3 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-18*
*Last updated: 2026-03-18 after roadmap creation*
