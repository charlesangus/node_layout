# Project Research Summary

**Project:** node_layout v1.1
**Domain:** Nuke DAG auto-layout plugin — incremental feature milestone
**Researched:** 2026-03-05
**Confidence:** HIGH

## Executive Summary

node_layout v1.1 extends an existing, validated Nuke Python plugin (~4,095 LOC) that
auto-arranges node graphs using a two-phase recursive tree algorithm (compute_dims +
place_subtree). The v1.1 milestone adds nine features: spacing rebalance, multi-input
fan alignment with mask side-swap, per-node state storage, horizontal B-spine layout,
axis-specific shrink/expand, expand push-away, Dot font-size margin scaling, Group
context bug fix, and command renames. Every feature builds on the existing engine
without replacing it — no new dependencies, no new modules, no algorithm rewrites.

The recommended build order is strictly dependency-driven: prefs groundwork first
(provides new pref keys needed by spacing and font-scaling), per-node state storage
second (enables horizontal replay and axis-mode memory), fan alignment third (modifies
the same core functions horizontal mode will later touch), axis-mode scale/expand
fourth, horizontal B-spine last (most invasive signature change, deferred until the
regression safety net from prior phases is in place). Two independent fixes — Group
context correction and command renames — are low-risk and can land early in any phase.

The dominant risk is silent data loss from Nuke's knob serialization behavior:
Python-side `addKnob()` calls do NOT write `addUserKnob` records into the .nk save
file, so per-node state is lost on script close unless the correct pattern
(`addUserKnob` via TCL or `addOnCreate` callback) is used. A secondary architectural
risk is memo cache collision when horizontal and vertical layout modes share the same
`compute_dims` memo dict. Both risks are well-understood and have clear prevention
strategies documented in the research.

## Key Findings

### Recommended Stack

No new libraries or dependencies are needed. All v1.1 work uses the existing Nuke
Python API (`nuke.Knob`, `nuke.Tab_Knob`, `nuke.Group.begin()/end()`, `xpos/ypos`,
`screenWidth/screenHeight`). The correct knob flags are `nuke.INVISIBLE | nuke.NO_RERENDER`
for state-storage knobs, and `nuke.INVISIBLE` alone for the Tab_Knob. The `DO_NOT_WRITE`
flag must not be set — it prevents values from persisting to the .nk file.

**Core API patterns:**
- `nuke.INVISIBLE | nuke.NO_RERENDER` on data knobs — hides knobs permanently, prevents render-hash dirtying
- `with context:` (Group context manager) for all `nuke.nodes.Dot()` calls — guarantees correct parent Group even if an exception is raised
- `node['note_font_size'].getValue()` — direct float read of Dot label font size (HIGH confidence, confirmed via Foundry examples)
- Axis swap for horizontal layout uses the existing `setXpos/setYpos/screenWidth/screenHeight` API — no new API surface required

See `.planning/research/STACK.md` for full pattern code examples.

### Expected Features

**Must have (table stakes) — v1.1 is incomplete without these:**
- Spacing rebalance (horizontal prefs added) — current spacing is too vertical-heavy; horizontal gap is absent from prefs entirely
- Multi-input fan alignment + mask side-swap — staircase for 2+ non-mask inputs is a known quality problem; mask-always-right causes clutter
- Per-node state storage — foundational for all replay; "least surprise re-layout" is the stated goal
- Group context bug fix — silent correctness bug; affects any DAG with Group nodes
- Command renames — pure menu.py; improves tab-menu discoverability with zero risk

**Should have (differentiators) — high value, requires state storage as prerequisite:**
- Horizontal B-spine layout command — addresses real workflow for left-to-right processing chains
- Shrink/Expand H/V/Both axis modes — users sometimes need axis-specific compression
- Expand push-away — natural completion of existing push logic; reduces manual cleanup after expand
- Dot font-size as subtree margin signal — lets compositor's own visual signals drive layout spacing

**Defer indefinitely:**
- Full Sugiyama/layered-graph layout — NP-hard general DAG layout; no benefit for tree-shaped Nuke DAGs
- Physics-based force layout — non-deterministic; incompatible with artist undo/redo expectations
- Visible GUI toggles on node parameter panels — clutter on every node; hidden knobs are correct UX
- Keyboard shortcut customization in prefs — explicitly out of scope from v1.0
- Layout for entire DAG without selection — unpredictable on complex scripts

See `.planning/research/FEATURES.md` for full feature dependency graph and UX edge cases.

### Architecture Approach

The existing module structure (node_layout.py, node_layout_prefs.py,
node_layout_prefs_dialog.py, menu.py, util.py, make_room.py) requires no new modules.
All v1.1 changes are contained within modifications to existing files, plus three new
private helper functions added to node_layout.py. The core call chain
(layout_upstream → insert_dot_nodes → compute_dims → place_subtree → push_nodes_to_make_room)
is preserved; state read/write wraps the entry points rather than penetrating the
recursive interior.

**Components modified:**
1. `node_layout.py` — primary change target; new helpers + modified core functions + new entry points for H/V axis modes and horizontal layout
2. `node_layout_prefs.py` — two new DEFAULTS keys (`horizontal_gap`, `dot_font_reference_size`)
3. `node_layout_prefs_dialog.py` — two new QLineEdit fields with populate/save wiring
4. `menu.py` — 8 new axis-mode entries, 2 new horizontal layout commands, command renames

**New private helpers (all in node_layout.py):**
1. `_write_node_state(node, layout_mode, scheme, scale_factor)` — idempotent; writes hidden tab + knobs
2. `_read_node_state(node)` — returns state dict or None; called at entry points only, never inside recursion
3. `_count_non_mask_side_inputs(input_slot_pairs, node)` — fan-mode branch condition

**Critical architecture rules:**
- State is read at entry points; never inside `compute_dims()` or `place_subtree()` — mixing per-node overrides mid-recursion breaks memoization
- `layout_mode` propagates as an explicit parameter (like `scheme_multiplier`), never via a module global
- Horizontal mode uses a dedicated `place_subtree_horizontal()` — not a swapped-argument call to the existing function
- `compute_dims` memo key must include axis to prevent cache collision between vertical and horizontal passes

See `.planning/research/ARCHITECTURE.md` for full data flow diagrams and per-feature integration analysis.

### Critical Pitfalls

1. **Knob values lost on script save/reload (Pitfall 1)** — `addKnob()` in Python does not write `addUserKnob` records to the .nk file. Prevention: use `addUserKnob` via TCL string or `addOnCreate` callback. This is the single highest-risk implementation decision; getting it wrong means the state-replay feature silently does nothing after a script reload.

2. **Group context: `nuke.nodes.Dot()` creates nodes in wrong Group (Pitfall 2 + 15)** — when a user runs layout while inside a Group DAG, `nuke.nodes.Dot()` creates nodes at root level. Additionally, `nuke.allNodes()` in push_nodes_to_make_room also defaults to root. Prevention: capture `current_group` at entry point, wrap all node creation with `with current_group:`, pass `group=current_group` to `nuke.allNodes()`.

3. **Memo cache collision in horizontal mode (Pitfall 3)** — sharing the `compute_dims` memo dict across vertical and horizontal passes causes stale cached results when a node is reachable from both. Prevention: include axis in memo key as `(id(node), layout_mode)` or use a separate `compute_dims_h` function.

4. **Axis swap silently breaks place_subtree X/Y semantics (Pitfall 4)** — Nuke's `setXpos/setYpos` always mean screen X and Y. A naive argument-transposition approach produces a mirrored layout, not a horizontal one. Prevention: implement a dedicated `place_subtree_horizontal()` sibling function with correct axis semantics throughout.

5. **Per-node knob reads inside recursion break memoization (Pitfall 5)** — reading per-node state inside `compute_dims()` makes cached results context-dependent; diamond paths then use wrong cached bounding boxes. Prevention: resolve all parameters at entry point before recursion begins; state is a replay hint, not a per-node mid-traversal override.

See `.planning/research/PITFALLS.md` for 15 total pitfalls including moderate and minor categories.

## Implications for Roadmap

Based on research, the natural phase structure follows feature dependency chains and
the principle of modifying `compute_dims` / `place_subtree` in the safest order.

### Phase 1: Prefs Groundwork + Command Renames + Group Context Fix

**Rationale:** These three items have zero algorithmic risk and establish the foundation
every subsequent phase depends on. New pref keys must exist before spacing or font-scaling
code references them. The Group context fix is a correctness bug that affects any phase
creating new Dot nodes. Command renames are pure menu.py with no side effects.
**Delivers:** Correct Group-scoped node creation, tab-menu discoverability improvement,
and new pref keys (`horizontal_gap`, `dot_font_reference_size`) ready for later phases.
**Addresses:** Table stakes features — command renames, Group context fix, foundation for spacing rebalance.
**Avoids:** Pitfalls 2, 14, 15 (group context, stale menu names, allNodes scope).

### Phase 2: Per-Node State Storage

**Rationale:** State storage is the dependency blocker for horizontal B-spine layout and
Shrink/Expand H/V/Both modes. Building it second, before any algorithm changes, means
every subsequent phase can immediately write and read state. It also has no dependencies
on the algorithm changes ahead.
**Delivers:** Hidden `node_layout_tab` knobs on all laid-out nodes; idempotent write/read
helpers; state persists across .nk script saves.
**Addresses:** Per-node state storage (differentiator); prerequisite for horizontal replay and axis modes.
**Avoids:** Pitfalls 1, 5, 11, 13 (knob serialization, recursion memo breakage, undo ordering, duplicate tabs).
**Research flag:** The knob serialization pattern (TCL addUserKnob vs addOnCreate) needs
a manual verification step: write a knob, save the .nk file, close Nuke, reopen, and confirm
the knob is present. This should be tested before the phase is marked complete.

### Phase 3: Dot Font-Size Margin Scaling

**Rationale:** Isolated single-function change to `_subtree_margin()`. No parameter
signature changes to `compute_dims` or `place_subtree`. Validating it now means those
functions have stable behavior before Phases 4-6 make larger modifications to them.
**Delivers:** Margin scaling based on Dot `note_font_size` knob; new `dot_font_reference_size` pref consumed.
**Addresses:** Dot font-size as subtree margin signal (differentiator).
**Avoids:** Pitfall 10 (never use `screenHeight()` after font change; compute height from font size value directly).

### Phase 4: Multi-Input Fan Alignment + Mask Side-Swap

**Rationale:** Fan alignment modifies `compute_dims()` and `place_subtree()` — the same
functions horizontal mode will modify in Phase 6. Implementing and testing fan alignment in
pure vertical mode first establishes a regression baseline and validates the dimensional
formulas before the larger horizontal mode change.
**Delivers:** Same-Y subtree roots for 2+ non-mask inputs; mask inputs placed left when non-mask fill the right side.
**Addresses:** Multi-input fan alignment + mask side-swap (differentiator, noted as high-value quality improvement).
**Avoids:** Pitfalls 6, 7 (staircase-vs-fan conflict requires spec clarification; mask detection false negatives require label inspection, not class expansion).
**Research flag:** Pitfall 6 requires spec clarification before coding: fan alignment in
vertical mode means aligning side-input Dot positions, not subtree roots. Confirm the
intended behavior (Dot alignment vs. subtree-root Y alignment) with the project owner
before implementation.

### Phase 5: Shrink/Expand H/V/Both + Expand Push-Away

**Rationale:** The axis parameter change to `_scale_selected_nodes` and the push-away
addition both touch the same `expand_*` wrappers. Doing them together avoids two refactor
passes over the same code. Push-away reuses `push_nodes_to_make_room()` which is already
tested and stable.
**Delivers:** 8 new axis-mode entry points (H/V variants of shrink/expand selected and upstream);
automatic push-away after expand operations; correct snap-floor behavior per axis.
**Addresses:** Shrink/Expand H/V/Both modes, Expand push-away (both differentiators).
**Avoids:** Pitfalls 8, 9 (double-push accumulation is inherent but must be documented; snap floor must not apply to non-scaled axis).

### Phase 6: Horizontal B-Spine Layout

**Rationale:** Most invasive change — adds `layout_mode` parameter to `compute_dims()` and
`place_subtree()`, propagating through all recursive calls. Deferred last so that the full
test coverage from Phases 1-5 provides a regression safety net. Per-node state storage
(Phase 2) must already be in place so `layout_mode="horizontal"` is stored and replayed
on subsequent normal layout runs.
**Delivers:** `layout_upstream_horizontal()` and `layout_selected_horizontal()` entry points;
left-to-right primary spine; automatic horizontal replay on normal re-layout via stored state.
**Addresses:** Horizontal B-spine layout (differentiator, high complexity).
**Avoids:** Pitfalls 3, 4 (memo key includes `layout_mode`; dedicated `place_subtree_horizontal()` rather than argument transposition).

### Phase Ordering Rationale

- Phases 1-2 are pure infrastructure: they have no visible user-facing behavior changes
  beyond the bug fix, but every other phase requires them.
- Phase 3 (Dot font scaling) is isolated and validates the stability of `_subtree_margin()`
  before the fan alignment phase modifies the functions that call it.
- Phase 4 (fan alignment) must precede Phase 6 (horizontal) because both modify
  `compute_dims()` and `place_subtree()`; stabilizing fan alignment first provides
  a regression baseline.
- Phases 5 and 6 are independent of each other and could swap order, but Phase 6 is
  the highest-risk change and benefits from Phase 5's menu.py additions already being
  in place.
- The Group context fix is grouped into Phase 1 because it affects Dot creation, which
  every phase from 4 onward depends on. Fixing it last would contaminate phases in between.

### Research Flags

Phases likely needing deeper research or verification during implementation:

- **Phase 2 (Per-Node State Storage):** The knob serialization mechanism (TCL `addUserKnob`
  vs. `addOnCreate` callback) must be empirically verified against the target Nuke version
  before committing to an approach. A minimal test script should be run in Nuke to confirm
  that knob values survive a save/close/reopen cycle.
- **Phase 4 (Fan Alignment):** The spec for "fan alignment" in vertical mode is ambiguous —
  whether it means aligning side-input Dot Y positions or subtree-root Y positions must be
  clarified before implementation. The two interpretations have meaningfully different
  implementations and complexity.

Phases with well-documented patterns (skip research-phase):

- **Phase 1 (Prefs + Renames + Group Fix):** All three are straightforward Nuke API patterns
  with HIGH-confidence sources. The Group context fix pattern is documented in official Foundry docs.
- **Phase 3 (Dot Font Scaling):** `note_font_size` knob name is HIGH confidence. The
  `_subtree_margin()` modification scope is contained to one function.
- **Phase 5 (Scale/Expand):** The `_scale_selected_nodes` axis parameter and
  `push_nodes_to_make_room` integration both follow established patterns already in the
  codebase. No new API patterns are involved.
- **Phase 6 (Horizontal B-spine):** The API (`xpos/ypos/screenWidth/screenHeight`) is
  identical to vertical mode. The architecture decision (dedicated `place_subtree_horizontal`
  function) is already resolved by research. No additional API research needed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All API patterns verified against official Foundry docs; no new dependencies; flag values confirmed via NDK reference |
| Features | HIGH | Feature set derived from direct codebase analysis and stated project requirements; community sources confirm UX expectations |
| Architecture | HIGH | Based on direct source-level analysis of all six existing modules; integration points are precise, not speculative |
| Pitfalls | HIGH | Critical pitfalls (knob serialization, group context, memo collision) confirmed by official API docs and community sources; test strategies are concrete |

**Overall confidence:** HIGH

### Gaps to Address

- **Knob serialization mechanism (TCL vs. addOnCreate):** FEATURES.md rates the
  `addUserKnob`/`addOnCreate` pattern at MEDIUM confidence (community + docs, not
  fully confirmed). Must be validated empirically in the target Nuke version before Phase 2
  implementation commits to an approach.
- **Dot `note_font_size` default value:** STACK.md notes the factory default is "20 (some
  sources cite 22)." Use `nuke.knobDefault("Dot.note_font_size")` at runtime to confirm
  the actual default in the deployment Nuke version before hardcoding the reference constant.
- **FEATURES.md cites `label_size` as the Dot font size knob name (LOW confidence),
  while STACK.md confirms `note_font_size` (HIGH confidence).** Use `note_font_size`.
  The discrepancy in FEATURES.md is a research artifact and should not create implementation
  ambiguity.
- **Fan alignment vertical-mode spec:** Whether same-Y means Dot alignment or subtree-root
  alignment is unresolved. This gap must be decided before Phase 4 begins.

## Sources

### Primary (HIGH confidence)
- [Foundry Nuke Python API — nuke.Knob](https://learn.foundry.com/nuke/developers/150/pythondevguide/_autosummary/nuke.knob.html) — knob flags, INVISIBLE vs HIDDEN vs DO_NOT_WRITE vs NO_RERENDER
- [Foundry Nuke Python API — nuke.Tab_Knob](https://learn.foundry.com/nuke/developers/140/pythonreference/_autosummary/nuke.Tab_Knob.html) — tab creation pattern
- [Foundry Nuke Python API — nuke.Group](https://learn.foundry.com/nuke/developers/140/pythonreference/_autosummary/nuke.Group.html) — begin/end context manager
- [Foundry NDK Developers Guide — Knob Flags](https://learn.foundry.com/nuke/developers/63/ndkdevguide/knobs-and-handles/knobflags.html) — hex values for flag constants
- [Manipulating the Node Graph — Nuke Python API Reference](https://learn.foundry.com/nuke/developers/130/pythondevguide/dag.html) — xpos/ypos/screenWidth/screenHeight
- [Foundry Nuke Python API — Undo](https://learn.foundry.com/nuke/developers/150/pythondevguide/_autosummary/nuke.Undo.html) — undo group ordering

### Secondary (MEDIUM confidence)
- [Nukepedia — Some Flags](http://www.nukepedia.com/python/some-flags) — flag values consistent with official NDK docs
- [Conrad Olson — Add Nodes Inside A Group With Python](https://conradolson.com/add-nodes-inside-a-group-with-python) — begin/end/with Group pattern
- [Ben McEwan — addOnCreate for persistent knobs](https://benmcewan.com/blog/2018/09/10/add-new-functionality-to-default-nodes-with-addoncreate/) — addOnCreate serialization pattern
- Nuke mailing list — screenHeight() staleness: https://www.mail-archive.com/nuke-python@support.thefoundry.co.uk/msg02764.html
- `note_font_size` knob name: multiple community sources citing `nuke.knobDefault("Dot.note_font_size", ...)`

### Tertiary (LOW confidence)
- `nuke.nodes.X` vs `nuke.createNode` group context behavior — Conrad Olson article (WebSearch only, needs Foundry official confirmation)
- Custom knob serialization via `addUserKnob` TCL pattern — community + knob docs (MEDIUM-LOW; empirical test required before committing)

---
*Research completed: 2026-03-05*
*Ready for roadmap: yes*
