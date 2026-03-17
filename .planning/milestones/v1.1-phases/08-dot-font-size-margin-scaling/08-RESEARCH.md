# Phase 8: Dot Font-Size Margin Scaling - Research

**Researched:** 2026-03-11
**Domain:** Python layout engine — Nuke DAG node margin computation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Scaling formula:**
- Linear ratio: `font_multiplier = font_size / dot_font_reference_size`
- Floor at 1.0 — a Dot with font size below the reference does NOT shrink the margin
- Cap at 4.0 — very large fonts (200px etc.) are clamped to 4× margin maximum
- Formula: `font_multiplier = min(max(font_size / reference_size, 1.0), 4.0)`

**Axes affected:**
- Both V-axis (`_subtree_margin`) and H-axis (`_horizontal_margin`) are scaled by the font multiplier
- Applies to all slots including the mask input slot (mask_input_ratio is already applied; font scale stacks on top)

**Stacking with other multipliers:**
- Font multiplier stacks multiplicatively with scheme multiplier, v_scale, and h_scale
- Composes freely — a big-font Dot under a Compact scheme can produce a margin that exceeds the base margin
- No override semantics; all three signals are independent

**Which Dot qualifies:**
- Walk upstream from `node.input(slot)` through consecutive Dot nodes
- Pick the first Dot with a non-empty label — that's the section-boundary marker
- Stop the walk immediately when encountering any non-Dot node
- If no labeled Dot is found before hitting a non-Dot (or if the immediate input is not a Dot), font_multiplier = 1.0 (no scaling)
- Diamond-resolution Dots (marked with `node_layout_diamond_dot` knob) are NOT special-cased; they will have empty labels in practice so they won't trigger scaling

**Example traversal:**
- Merge → Dot1 (no label) → Dot2 (labeled "BG elements") → Grade → Dot3
- Result: use Dot2's font size (first labeled Dot in the consecutive chain from the slot)
- Merge → Dot1 (no label) → Grade → Dot3 (labeled)
- Result: multiplier = 1.0 (chain broke at Grade; Dot3 is not reachable)

### Claude's Discretion
- Whether `_dot_font_scale(node, slot)` is a standalone helper or inlined
- How to read `note_font_size` knob from Dot nodes (check knob existence safely)
- Where in `compute_dims()` / `place_subtree()` to inject the font_multiplier (alongside the existing v_scale/h_scale application)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LAYOUT-03 | Subtree margin scales with the font size of the Dot node at the subtree root — a larger font signals a section boundary and produces more breathing room | Fully supported: scaling formula locked in CONTEXT.md; injection points identified in `_subtree_margin()` and `_horizontal_margin()`; Dot knob read pattern established (`try/except` on `note_font_size`) |
</phase_requirements>

---

## Summary

Phase 8 is a pure computation enhancement: it adds a `font_multiplier` scalar that is applied on top of existing margin scaling. There are exactly two margin call sites in `node_layout.py` — `_subtree_margin()` for the V-axis and `_horizontal_margin()` for the H-axis. Both are called in `compute_dims()` and `place_subtree()` via list comprehensions that build `side_margins_v` and `side_margins_h`. The font multiplier needs to be computed per-slot (because each slot may connect to a different Dot chain) and applied in those same comprehensions.

The `dot_font_reference_size` pref (default: 20) is already declared in `DEFAULTS`, already read/written by the prefs dialog (`dot_font_reference_size_edit`), and already saved/loaded by `NodeLayoutPrefs`. The stub was put in place during Phase 6; this phase wires it into actual computation. No pref infrastructure changes are needed.

The Nuke knob that stores a Dot's label font size is `note_font_size` (an Int_Knob or similar). It must be read defensively with `try/except (KeyError, AttributeError)` — the project's established pattern for any Nuke API call that may fail. If the knob is absent, treat font size as the reference size (multiplier = 1.0).

**Primary recommendation:** Implement `_dot_font_scale(node, slot)` as a standalone module-level helper in `node_layout.py`. Apply its result multiplicatively in the `side_margins_v` and `side_margins_h` comprehensions in both `compute_dims()` and `place_subtree()`. No changes needed to prefs, state, dialog, or entry-point functions.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python 3 stdlib | — | `math`, `ast`, `unittest` | Already in use throughout the project |
| Nuke Python API | 11+ | `node.knob()`, `node.input()` | Target runtime; Nuke 11+ assumed per REQUIREMENTS.md |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `node_layout_prefs.prefs_singleton` | project | Read `dot_font_reference_size` | Already the canonical pref accessor |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Standalone `_dot_font_scale()` helper | Inline logic inside margin helpers | Standalone is testable in isolation; inline would require full node wiring in margin tests |
| Applying multiplier in margin helpers | Applying at call sites in comprehensions | Margin helpers already have the slot context needed for the Dot walk; cleaner to keep the computation there |

---

## Architecture Patterns

### Recommended Project Structure
No new files needed. All changes are within:
```
node_layout.py          # add _dot_font_scale(), modify _subtree_margin(), _horizontal_margin()
tests/
└── test_dot_font_scale.py   # new test file for Phase 8
```

### Pattern 1: Dot Walk Helper
**What:** A module-level function that walks upstream from a given slot through consecutive Dot nodes and returns the font multiplier for the first labeled Dot found.
**When to use:** Called inside `_subtree_margin()` and `_horizontal_margin()` (or at the comprehension layer — see discretion area).
**Example:**
```python
def _dot_font_scale(node, slot):
    """Return the font multiplier for the labeled-Dot walk from node.input(slot).

    Walks consecutive Dot nodes upstream from the given slot.  Returns the font
    multiplier for the first Dot that has a non-empty label.  Returns 1.0 if no
    labeled Dot is found before the chain ends.
    """
    current_prefs = node_layout_prefs.prefs_singleton
    reference_size = current_prefs.get("dot_font_reference_size")
    candidate = node.input(slot)
    while candidate is not None and candidate.Class() == 'Dot':
        try:
            label = candidate['label'].value()
        except (KeyError, AttributeError):
            label = ''
        if label.strip():
            try:
                font_size = int(candidate['note_font_size'].value())
            except (KeyError, AttributeError, ValueError):
                font_size = reference_size
            return min(max(font_size / reference_size, 1.0), 4.0)
        candidate = candidate.input(0)
    return 1.0
```

### Pattern 2: Multiplicative Injection in Margin Helpers
**What:** Compute `font_multiplier` inside each margin helper and multiply the result before returning.
**When to use:** This is where `node` and `slot` are already in scope, so no extra parameters are needed at the comprehension layer.

Current `_subtree_margin()` returns:
```python
effective_margin = int(base * mode_multiplier * math.sqrt(node_count) / math.sqrt(reference_count))
```

After Phase 8, the return becomes:
```python
font_mult = _dot_font_scale(node, slot)
effective_margin = int(base * mode_multiplier * math.sqrt(node_count) / math.sqrt(reference_count) * font_mult)
```

The mask ratio is applied after:
```python
if _is_mask_input(node, slot):
    ratio = current_prefs.get("mask_input_ratio")
    return int(effective_margin * ratio)
return effective_margin
```

Current `_horizontal_margin()` returns a raw pref value. After Phase 8:
```python
font_mult = _dot_font_scale(node, slot)
if _is_mask_input(node, slot):
    return int(current_prefs.get("horizontal_mask_gap") * font_mult)
return int(current_prefs.get("horizontal_subtree_gap") * font_mult)
```

### Pattern 3: Established Knob Read with Defensive Fallback
**What:** Read `note_font_size` from a Dot node using `try/except (KeyError, AttributeError)`.
**When to use:** Every Nuke knob access in this codebase uses this guard pattern.
**Key insight:** If the knob is absent or raises, fall back to `reference_size` so the multiplier resolves to 1.0 (no scaling), preserving backward compatibility.

### Pattern 4: Consecutive-Dot Walk Termination
**What:** Walk `candidate = candidate.input(0)` in a while loop. Stop when `candidate is None` or `candidate.Class() != 'Dot'`.
**Why the loop works:** `_get_input_slot_pairs` follows the same `node.input(i)` access pattern. Dot nodes have exactly one input (`input(0)`). The walk does not need to cross non-Dot nodes.

### Anti-Patterns to Avoid
- **Reading font_multiplier at entry points (layout_upstream / layout_selected):** Unlike scheme/h_scale/v_scale, font_multiplier is slot-specific (each slot may connect to a different Dot chain). It cannot be pre-computed per-node at entry. It must be computed lazily inside the margin helper at the moment the slot is known.
- **Adding font_multiplier to the memo key:** The memo key `(id(node), scheme_multiplier, node_h_scale, node_v_scale)` should NOT include font_multiplier — the font multiplier is already folded into the margin value when `_subtree_margin()` / `_horizontal_margin()` are called. The memo stores `(W, H)` which already reflects the font-scaled margins.
- **Modifying `compute_dims()` / `place_subtree()` signatures:** No new parameters are needed. The font multiplier is encapsulated inside the margin helpers where node and slot are already available.
- **Treating labeled diamond-resolution Dots as section markers:** Diamond Dots have empty labels in practice so the walk skips them naturally; no special-case needed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pref access | Custom config reader | `node_layout_prefs.prefs_singleton.get("dot_font_reference_size")` | Already implemented, tested, and file-backed |
| Knob existence check | `hasattr` or custom guard | `try/except (KeyError, AttributeError)` | Project-established pattern for all Nuke API calls |

**Key insight:** The `dot_font_reference_size` pref is already in DEFAULTS (value 20), already displayed in the dialog, already saved/loaded. Phase 8 only needs to read it — nothing to build in the pref layer.

---

## Common Pitfalls

### Pitfall 1: `note_font_size` knob name
**What goes wrong:** Using the wrong knob name. Nuke's Dot node stores label font size in the knob named `note_font_size` (not `font_size`, `label_font_size`, or `text_size`).
**Why it happens:** The Nuke knob naming is not obvious from the knob label in the UI.
**How to avoid:** Use `node['note_font_size']` and wrap in `try/except (KeyError, AttributeError)` so a wrong name fails silently to the fallback.
**Warning signs:** Always getting multiplier 1.0 even with large-font Dots — check the knob name first.

### Pitfall 2: Forgetting the Floor at 1.0
**What goes wrong:** A Dot with font size 10 (below reference 20) would compute `10/20 = 0.5`, shrinking the margin.
**Why it happens:** The formula without the floor produces sub-1 multipliers for small fonts.
**How to avoid:** Always apply `max(font_size / reference_size, 1.0)` before the cap. The locked formula `min(max(font_size / reference_size, 1.0), 4.0)` handles this correctly.
**Warning signs:** Default-font Dots (font_size ≈ reference_size) returning multiplier ≠ 1.0.

### Pitfall 3: Memo Key Collision If Font Multiplier Were Added
**What goes wrong:** If someone were to add font_multiplier to the memo key to try to "fix" caching, it would silently break because the multiplier is slot-specific and the memo is keyed per-node (not per-slot).
**Why it happens:** The memo design pre-dates this feature.
**How to avoid:** Do not change the memo key. The font multiplier is baked into the margin values at computation time — the memo correctly caches the final `(W, H)` which incorporates font-scaled margins.

### Pitfall 4: Walk into Non-Dot Nodes
**What goes wrong:** Continuing the Dot walk past a non-Dot node (e.g., walking into a Grade node's inputs).
**Why it happens:** Forgetting the `candidate.Class() != 'Dot'` termination check.
**How to avoid:** The while condition `candidate.Class() == 'Dot'` ensures the walk stops at the first non-Dot. The labeled Dot search is strictly limited to the consecutive Dot chain.

### Pitfall 5: Integer Truncation on the Multiplied Margin
**What goes wrong:** Applying `int()` before the font multiplier is applied, discarding the fractional component.
**Why it happens:** `_subtree_margin()` currently calls `int()` on the effective_margin before returning. If the multiplier is applied after `int()`, small reference margins lose precision.
**How to avoid:** Compute `int(base * mode_multiplier * sqrt_factor * font_mult)` in one step so `int()` is applied once at the end after all multipliers are combined.

---

## Code Examples

### _dot_font_scale() — full implementation sketch
```python
# Source: derived from project patterns (node.input, node.Class, try/except for knobs)
def _dot_font_scale(node, slot):
    current_prefs = node_layout_prefs.prefs_singleton
    reference_size = current_prefs.get("dot_font_reference_size")
    candidate = node.input(slot)
    while candidate is not None and candidate.Class() == 'Dot':
        try:
            label = candidate['label'].value()
        except (KeyError, AttributeError):
            label = ''
        if label.strip():
            try:
                font_size = int(candidate['note_font_size'].value())
            except (KeyError, AttributeError, ValueError):
                font_size = reference_size
            return min(max(font_size / reference_size, 1.0), 4.0)
        candidate = candidate.input(0)
    return 1.0
```

### Modified _subtree_margin() — injection point
```python
# Source: node_layout.py lines 119-129, extended for Phase 8
def _subtree_margin(node, slot, node_count, mode_multiplier=None):
    current_prefs = node_layout_prefs.prefs_singleton
    base = current_prefs.get("base_subtree_margin")
    if mode_multiplier is None:
        mode_multiplier = current_prefs.get("normal_multiplier")
    reference_count = current_prefs.get("scaling_reference_count")
    font_mult = _dot_font_scale(node, slot)
    effective_margin = int(base * mode_multiplier * math.sqrt(node_count) / math.sqrt(reference_count) * font_mult)
    if _is_mask_input(node, slot):
        ratio = current_prefs.get("mask_input_ratio")
        return int(effective_margin * ratio)
    return effective_margin
```

### Modified _horizontal_margin() — injection point
```python
# Source: node_layout.py lines 132-141, extended for Phase 8
def _horizontal_margin(node, slot):
    current_prefs = node_layout_prefs.prefs_singleton
    font_mult = _dot_font_scale(node, slot)
    if _is_mask_input(node, slot):
        return int(current_prefs.get("horizontal_mask_gap") * font_mult)
    return int(current_prefs.get("horizontal_subtree_gap") * font_mult)
```

### Stub Dot node for tests (label + note_font_size knobs)
```python
# Pattern for building a labeled Dot stub with a specific font size in tests
class _StubKnob:
    def __init__(self, val):
        self._val = val
    def value(self):
        return self._val

class _StubDotNode(_StubNode):
    def __init__(self, label='', font_size=20):
        super().__init__(node_class='Dot')
        self._knobs['label'] = _StubKnob(label)
        self._knobs['note_font_size'] = _StubKnob(font_size)
    def input(self, i):
        return self._upstream if i == 0 else None
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `dot_font_reference_size` unused (stub only) | Active: read in `_dot_font_scale()` | Phase 8 | Unlocks font-size scaling |
| `_subtree_margin()` ignores Dot font | `_subtree_margin()` multiplied by `_dot_font_scale()` | Phase 8 | Larger-font section Dots produce more V-margin |
| `_horizontal_margin()` ignores Dot font | `_horizontal_margin()` multiplied by `_dot_font_scale()` | Phase 8 | Same — more H-margin for section Dots |

**Deprecated/outdated:**
- Nothing is removed in this phase. The pref key was already in DEFAULTS; it becomes active.

---

## Open Questions

1. **Exact knob name for Dot label font size in Nuke**
   - What we know: Nuke Dot nodes store label-related properties as knobs; the label text knob is `label`; the font size knob is conventionally named `note_font_size` in Nuke's internal schema
   - What's unclear: Cannot be verified via Context7 (no Nuke SDK in library); cannot be tested without a live Nuke runtime
   - Recommendation: Implement with `candidate['note_font_size']` wrapped in `try/except (KeyError, AttributeError)` with fallback to `reference_size`. If the knob name is wrong, the fallback fires, multiplier = 1.0, and no regression occurs. Manual smoke-test in Nuke with an actual Dot node will confirm the name immediately.

2. **Default font size value on a factory-fresh Dot**
   - What we know: The reference pref is 20; the Nuke UI default for `note_font_size` on a Dot is typically around 20 (matching the pref default)
   - What's unclear: Cannot confirm without a live Nuke session
   - Recommendation: The floor of 1.0 in the formula means any font size at or below the reference produces multiplier = 1.0, so the exact factory default only matters for the no-regression criterion. If the factory default equals the pref default (both 20), the criterion is automatically satisfied.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Python `unittest` (stdlib) |
| Config file | none — tests run via `unittest discover` or direct execution |
| Quick run command | `python3 -m unittest discover -s /workspace/tests -p "test_dot_font_scale.py" -v` |
| Full suite command | `python3 -m unittest discover -s /workspace/tests -v` |

**Baseline:** 203 tests, all passing as of 2026-03-11.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LAYOUT-03 | `_dot_font_scale()` returns 1.0 when no Dot at slot | unit | `python3 -m unittest tests.test_dot_font_scale.TestDotFontScaleUnit.test_no_dot_returns_1` | Wave 0 |
| LAYOUT-03 | `_dot_font_scale()` returns 1.0 for unlabeled Dot chain | unit | `python3 -m unittest tests.test_dot_font_scale.TestDotFontScaleUnit.test_unlabeled_dot_chain_returns_1` | Wave 0 |
| LAYOUT-03 | `_dot_font_scale()` returns correct multiplier for labeled Dot with font_size=40, reference=20 | unit | `python3 -m unittest tests.test_dot_font_scale.TestDotFontScaleUnit.test_labeled_dot_font_40_reference_20` | Wave 0 |
| LAYOUT-03 | `_dot_font_scale()` floor: font_size below reference still returns 1.0 | unit | `python3 -m unittest tests.test_dot_font_scale.TestDotFontScaleUnit.test_floor_at_1` | Wave 0 |
| LAYOUT-03 | `_dot_font_scale()` cap: font_size/reference > 4 clamped to 4.0 | unit | `python3 -m unittest tests.test_dot_font_scale.TestDotFontScaleUnit.test_cap_at_4` | Wave 0 |
| LAYOUT-03 | `_dot_font_scale()` skips unlabeled Dot, finds labeled Dot2 in chain | unit | `python3 -m unittest tests.test_dot_font_scale.TestDotFontScaleUnit.test_walk_skips_unlabeled_finds_labeled` | Wave 0 |
| LAYOUT-03 | Walk stops at non-Dot: labeled Dot beyond a Grade is not found | unit | `python3 -m unittest tests.test_dot_font_scale.TestDotFontScaleUnit.test_walk_stops_at_non_dot` | Wave 0 |
| LAYOUT-03 | `_subtree_margin()` incorporates font_multiplier for labeled Dot | unit | `python3 -m unittest tests.test_dot_font_scale.TestSubtreeMarginFontScale.test_font_scale_applies` | Wave 0 |
| LAYOUT-03 | `_horizontal_margin()` incorporates font_multiplier for labeled Dot | unit | `python3 -m unittest tests.test_dot_font_scale.TestHorizontalMarginFontScale.test_font_scale_applies` | Wave 0 |
| LAYOUT-03 | Default-font Dot produces same margins as pre-Phase-8 (no regression) | unit | `python3 -m unittest tests.test_dot_font_scale.TestNoRegression.test_default_font_no_change` | Wave 0 |
| LAYOUT-03 | `note_font_size` knob absent falls back to reference (multiplier = 1.0) | unit | `python3 -m unittest tests.test_dot_font_scale.TestDotFontScaleUnit.test_missing_knob_fallback` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m unittest discover -s /workspace/tests -p "test_dot_font_scale.py" -v`
- **Per wave merge:** `python3 -m unittest discover -s /workspace/tests -v` (full 200+ suite)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `/workspace/tests/test_dot_font_scale.py` — covers all LAYOUT-03 test IDs above (new file; does not exist yet)

---

## Sources

### Primary (HIGH confidence)
- `/workspace/node_layout.py` — direct source read; `_subtree_margin()` (lines 119–129), `_horizontal_margin()` (lines 132–141), `compute_dims()` (lines 285–338), `place_subtree()` (lines 341–511)
- `/workspace/node_layout_prefs.py` — direct source read; `DEFAULTS` includes `dot_font_reference_size: 20`; `prefs_singleton.get()` is the canonical read accessor
- `/workspace/node_layout_prefs_dialog.py` — direct source read; `dot_font_reference_size_edit` is already wired; Phase 6 stub is complete
- `/workspace/.planning/phases/08-dot-font-size-margin-scaling/08-CONTEXT.md` — user locked decisions; scaling formula, axes, stacking, walk rules all confirmed

### Secondary (MEDIUM confidence)
- `/workspace/tests/test_horizontal_margin.py` — confirms `_StubNode` pattern, `_reset_prefs()` pattern, AST + behavioral test structure
- `/workspace/tests/test_margin_symmetry.py` — confirms `_PREFS_DEFAULTS` dict (must include all 10 keys), `_StubDotNode` creation pattern
- `/workspace/.planning/STATE.md` — confirms `try/except/else` for Nuke API, `State reads at entry points only`, knob access guard pattern

### Tertiary (LOW confidence)
- Nuke `note_font_size` knob name — derived from Nuke convention knowledge; must be verified in live Nuke session (flagged in Open Questions)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use; no new dependencies
- Architecture: HIGH — injection points confirmed by direct source read; patterns consistent with established project conventions
- Pitfalls: HIGH for formula/memo/truncation pitfalls (code-verified); MEDIUM for `note_font_size` knob name (cannot verify without live Nuke)

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable domain; pref/margin infrastructure is not actively changing)
