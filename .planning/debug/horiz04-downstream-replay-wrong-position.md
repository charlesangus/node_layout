---
status: resolved
trigger: "Horizontal subtree placed ABOVE downstream node instead of to its RIGHT"
created: 2026-03-15T00:00:00Z
updated: 2026-03-15T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED — spine_x/spine_y in the downstream-consumer path compute coordinates ABOVE the consumer (E), not to its RIGHT
test: read layout_upstream lines 1309-1335 and compare to place_subtree_horizontal docstring (root placed at spine_x, spine_y)
expecting: spine_x is E.xpos() + centering offset (not E.xpos() + E.screenWidth() + gap), spine_y is above E
next_action: DONE — root cause confirmed, diagnosis returned

## Symptoms

expected: Running Layout Upstream on downstream node E (whose input(0) chain carries mode='horizontal') places the horizontal subtree (A-B-C-D) to the RIGHT of E, at roughly E's Y level
actual: The horizontal subtree is placed directly ABOVE E (negative Y direction), not to its right
errors: none (silent wrong placement)
reproduction: Lay out a chain horizontally (A-B-C-D), connect D to E. Select E, run Layout Upstream.
started: introduced in commit 8ef07b9 (ancestor walk added)

## Eliminated

(none — root cause found on first investigation)

## Evidence

- timestamp: 2026-03-15T00:00:00Z
  checked: place_subtree_horizontal docstring (lines 518-558) and parameter semantics
  found: |
    "Root is placed at (spine_x, spine_y). Each input[0] ancestor that belongs to
    the spine is placed one step to the LEFT."
    root = rightmost node in the spine (D in the example).
    spine_x = X position for the root node (D's final X).
    spine_y = baseline Y position for the spine.
  implication: spine_x and spine_y are the final DAG coordinates where D will land.
    To place D to the RIGHT of E, spine_x must be E.xpos() + E.screenWidth() + gap.
    To place D at E's Y level, spine_y must be E.ypos() (approximately).

- timestamp: 2026-03-15T00:00:00Z
  checked: layout_upstream lines 1309-1325 (the downstream-consumer path)
  found: |
    if root is not original_selected_root:
        loose_gap_multiplier = current_prefs.get("loose_gap_multiplier")
        loose_gap = int(loose_gap_multiplier * root_scheme_multiplier * snap_threshold)
        _DOT_TILE_HEIGHT = 12
        spine_x = (original_selected_root.xpos()
                   + (original_selected_root.screenWidth() - root.screenWidth()) // 2)
        spine_y = (original_selected_root.ypos()
                   - loose_gap - _DOT_TILE_HEIGHT - loose_gap
                   - root.screenHeight())
  implication: |
    spine_x: approximately E.xpos() (with a centering offset based on width difference).
      This is the SAME X as E, not to E's right.
    spine_y: E.ypos() MINUS a large upward offset (two loose_gaps + dot height + node height).
      This is ABOVE E, not at the same Y level.
    Both values replicate the "place a node centred above a downstream consumer" logic
    used by vertical layout — but horizontal layout needs the OPPOSITE: place to the RIGHT,
    at the SAME Y.

- timestamp: 2026-03-15T00:00:00Z
  checked: vertical place_subtree call in layout_upstream line 1340
  found: |
    place_subtree(root, root.xpos(), root.ypos(), memo, ...)
    In the vertical path, root's own current xpos/ypos are used. The subtree is rebuilt
    in place starting from root's position.
  implication: vertical path does not use original_selected_root coordinates at all.
    The coordinate anchoring logic in the horizontal-downstream path was a new addition
    (commit 8ef07b9) but was written with vertical semantics.

- timestamp: 2026-03-15T00:00:00Z
  checked: layout_selected lines 1475-1476 (the non-downstream-consumer horizontal path)
  found: |
    place_subtree_horizontal(
        root, root.xpos(), root.ypos(), ...)
  implication: When the selected node IS the horizontal root (no ancestor walk needed),
    root's own current coordinates are used — the same pattern as vertical. This is correct
    for direct selection. The bug only affects the downstream-consumer branch.

- timestamp: 2026-03-15T00:00:00Z
  checked: layout_selected lines 1439-1476 — does layout_selected have the same bug?
  found: |
    After the BFS walk rebinds root to the horizontal ancestor, layout_selected calls:
        place_subtree_horizontal(root, root.xpos(), root.ypos(), ...)
    There is NO downstream-consumer coordinate override. It unconditionally uses the
    (rebound) root node's current xpos/ypos.
  implication: layout_selected avoids the explicit wrong-coordinate block entirely, but
    it also does NOT anchor relative to the original selected node — it uses the
    horizontal root's scrambled/stale coordinates instead. This is a different (subtler)
    problem: the chain will be placed wherever D happens to be sitting, which may be
    wrong after the graph has been modified. However, that is a separate issue from the
    symptom reported. The symptom (ABOVE instead of RIGHT) is in layout_upstream only.

## Resolution

root_cause: |
  layout_upstream lines 1313-1321: when the BFS ancestor walk finds that root is not
  the originally selected node (i.e. the user selected a downstream consumer E),
  the code computes spine_x and spine_y using the VERTICAL placement formula —
  centring D horizontally over E and placing it above E by a gap. This is correct
  for vertical layout but wrong for horizontal.

  place_subtree_horizontal places root (D, the rightmost spine node) AT (spine_x, spine_y).
  The rest of the spine (C, B, A) extends LEFTWARD from D.
  For the spine to appear to the RIGHT of E:
    - spine_x must be E.xpos() + E.screenWidth() + horizontal_gap  (D to the right of E)
    - spine_y must be E.ypos()  (D at the same vertical level as E)

  Currently:
    spine_x = E.xpos() + (E.screenWidth() - D.screenWidth()) // 2   -- SAME X as E, wrong
    spine_y = E.ypos() - loose_gap - 12 - loose_gap - D.screenHeight()  -- ABOVE E, wrong

  What it should be:
    spine_x = E.xpos() + E.screenWidth() + horizontal_gap
    spine_y = E.ypos()
    (where horizontal_gap = int(current_prefs.get("horizontal_subtree_gap") * root_scheme_multiplier))

fix: |
  In layout_upstream, replace lines 1313-1321 with:

    if root is not original_selected_root:
        horizontal_gap = int(
            current_prefs.get("horizontal_subtree_gap") * root_scheme_multiplier * snap_threshold
        )
        spine_x = original_selected_root.xpos() + original_selected_root.screenWidth() + horizontal_gap
        spine_y = original_selected_root.ypos()
    else:
        spine_x = root.xpos()
        spine_y = root.ypos()

  NOTE: Check whether horizontal_subtree_gap is already in pixel units or needs to be
  multiplied by snap_threshold. Compare with line 568:
    step_x = int(current_prefs.get("horizontal_subtree_gap") * scheme_multiplier)
  — no snap_threshold multiplication there. So the correct formula is probably:
    horizontal_gap = int(current_prefs.get("horizontal_subtree_gap") * root_scheme_multiplier)
  (without snap_threshold), consistent with how step_x is computed inside place_subtree_horizontal.

  For layout_selected: the same BFS walk rebinds root but then unconditionally uses
  root.xpos()/root.ypos() (lines 1475-1476). This means it uses the horizontal
  root D's stale coordinates rather than anchoring to the originally selected node.
  A parallel fix should save the original root before the BFS and apply the same
  spine_x/spine_y formula when root was rebound.

verification: applied — fixed by commit 6658d7b
files_changed:
  - node_layout.py
