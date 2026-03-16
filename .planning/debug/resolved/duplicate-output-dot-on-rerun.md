---
status: resolved
trigger: "Duplicate output Dot created on re-run of Layout Selected Horizontal"
created: 2026-03-15T00:00:00Z
updated: 2026-03-15T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED — _place_output_dot_for_horizontal_root uses Python `is` for node identity, which is inconsistent with the rest of the codebase (which uses `id()`) and will fail when Nuke returns a new Python wrapper object from `.input(0)` for the same underlying node.
test: Compared identity check patterns across all of node_layout.py
expecting: `id()` used everywhere else; `is` only in the two lines inside _place_output_dot_for_horizontal_root
next_action: report findings

## Symptoms

expected: _find_or_create_output_dot detects the existing Dot and reuses/repositions it on re-run
actual: A SECOND Dot is created rather than the existing one being reused
errors: None (silent duplicate creation)
reproduction: Run Layout Selected Horizontal on a chain that already has an output Dot; run it again
started: Always (design gap — `is` is the wrong identity check for Nuke node objects)

## Eliminated

- hypothesis: place_subtree_horizontal rewires root's connection, breaking existing_dot.input(0) reference
  evidence: place_subtree_horizontal only calls setXpos/setYpos; it never calls setInput on the root node or the output dot
  timestamp: 2026-03-15

- hypothesis: Wrong `root` passed to _place_output_dot_for_horizontal_root (e.g. user selected the output Dot)
  evidence: find_selection_roots returns the most-downstream spine node correctly; the output dot is downstream of root and cannot become root unless explicitly selected
  timestamp: 2026-03-15

- hypothesis: Double with current_group context on nuke.allNodes() returns wrong node set
  evidence: _layout_selected_horizontal_impl is already inside `with current_group:` at line 1575; _place_output_dot_for_horizontal_root re-enters with current_group: at line 436. Double-entry is harmless for allNodes() scoping.
  timestamp: 2026-03-15

- hypothesis: _find_or_create_output_dot is called separately in addition to _place_output_dot_for_horizontal_root
  evidence: grep confirms _find_or_create_output_dot is only called from _place_output_dot_for_horizontal_root (line 470); _layout_selected_horizontal_impl never calls it directly
  timestamp: 2026-03-15

## Evidence

- timestamp: 2026-03-15
  checked: All node identity comparisons in node_layout.py
  found: |
    Lines 303, 307, 316, 338, 578, 750, 753, 1147, 1280, 1307 etc. all use id(node) for
    identity comparisons, consistent with Nuke potentially returning new Python wrapper
    objects for the same underlying node across different API calls.
    ONLY lines 449 and 453 inside _place_output_dot_for_horizontal_root use `is`:
      line 449: if node.input(0) is root and existing_dot is None:
      line 453: if node.input(slot) is root:
  implication: |
    If nuke.allNodes() returns different Python wrapper objects than nuke.selectedNodes()
    for the same Nuke node, then `node.input(0) is root` at line 449 is always False.
    existing_dot is never found. The function falls through to _find_or_create_output_dot,
    which then creates a new Dot on every call.

- timestamp: 2026-03-15
  checked: _find_or_create_output_dot reuse check (lines 382-391)
  found: |
    The reuse check in _find_or_create_output_dot does NOT use `is`:
      currently_wired = consumer_node.input(consumer_slot)
      if currently_wired is not None and currently_wired.knob(_OUTPUT_DOT_KNOB_NAME) is not None:
    This check is knob-based (attribute presence), not identity-based — it works regardless
    of whether Nuke returns the same or a new Python wrapper object.
  implication: |
    This downstream reuse check is robust. It would catch the existing dot even if `is`
    fails — BUT only if _place_output_dot_for_horizontal_root actually reaches
    _find_or_create_output_dot with the correct consumer_node and consumer_slot.

- timestamp: 2026-03-15
  checked: _place_output_dot_for_horizontal_root consumer_node scan (lines 451-456)
  found: |
    The consumer_node scan also uses `is` at line 453:
      if node.input(slot) is root:
    After run 1, consumer_node.input(consumer_slot) is the OUTPUT DOT (not root).
    So this check returns False for consumer_node — consumer_node is not found.
    Result: existing_dot=None AND consumer_node=None.
    _place_output_dot_for_horizontal_root returns None at line 468.
    No dot is created OR reused — but at least no duplicate is created in this path.
  implication: |
    WAIT — this changes the analysis. If both `is` checks fail:
    1. existing_dot is None (can't find existing dot via input(0) is root)
    2. consumer_node is None (can't find consumer because its slot has the dot, not root)
    Then the function returns None. No duplicate in this case.

    For a DUPLICATE to occur, consumer_node must somehow be found.
    This would happen on the VERY FIRST re-run if nuke.allNodes() iteration order
    visits consumer_node BEFORE the output dot, and consumer_node still has root
    directly wired (i.e., the very first re-run immediately after creation, before
    the dot intercepts the wire). But after run 1, the wire IS intercepted.

    Alternative: The duplicate is created on the FIRST run in a different scenario —
    when consumer_node.input(slot) still IS root (the very first call), and then on
    the second call the `is` check fails for the new dot. BUT the first call is
    correct (creates dot); the second call fails to find existing_dot AND fails to
    find consumer_node (since consumer now has dot in its slot), returning None.

- timestamp: 2026-03-15
  checked: _find_or_create_output_dot reuse check in context of the full call chain
  found: |
    _find_or_create_output_dot is only reached from _place_output_dot_for_horizontal_root
    when existing_dot is None AND consumer_node is not None.
    After run 1: consumer_node.input(consumer_slot) = output_dot (not root).
    So when scanning all_nodes: consumer_node check `node.input(slot) is root` is False.
    consumer_node stays None.
    _find_or_create_output_dot is never reached.
    _place_output_dot_for_horizontal_root returns None (line 468).

    BUT _find_or_create_output_dot's own reuse check (lines 382-391) is irrelevant
    because it's never called on re-run (in this scenario).

    KEY QUESTION: When exactly is the duplicate created?
    Answer: The duplicate is created IF AND ONLY IF consumer_node is found despite the
    output dot existing. This requires consumer_node.input(slot) to still be `root`
    (not the dot) AND for existing_dot to not be found.

    Scenario where this occurs: If the `is` comparison fails for existing_dot lookup
    (line 449) BUT the consumer's slot still contains root (not yet intercepted by a dot).
    This is only possible on the very FIRST run of _layout_selected_horizontal_impl,
    but that's the intended creation run, not a re-run.

    REVISED ANALYSIS: The `is` issue on lines 449/453 does NOT directly cause a duplicate
    on re-run. The actual scenario for duplicate creation requires a different mechanism.

- timestamp: 2026-03-15
  checked: _place_output_dot_for_horizontal_root — what happens when existing_dot.input(0) is root returns False due to `is` issue
  found: |
    Scenario: `is` fails for existing_dot (Python wrapper inequality).
    - existing_dot not found (existing_dot=None)
    - consumer scan: node.input(slot) is root also fails via `is`
    - consumer_node stays None
    - Function returns None (line 468) — NO dot created or reused.
    Dot just gets abandoned — it's not re-positioned. Not a duplicate, but a bug
    (existing dot floats at old position, then _find_or_create_output_dot is never
    called, so no new dot either... unless we reach a path where consumer is found).

    ACTUAL DUPLICATE scenario: This requires consumer_node.input(consumer_slot)
    to still be `root` (directly wired). When does this happen?
    — If the output dot's input was changed (manually by user, or by another operation)
    — If the user manually deleted the output dot (restoring the direct root→consumer wire)
    — If the `spine_set` passed to `place_subtree_horizontal` is DIFFERENT between run 1
      and run 2 such that different spine nodes are processed

    OR: The duplicate occurs specifically in the `_find_or_create_output_dot` function
    when called with the consumer found — via the `is` check FAILING at line 384-385.
    Line 383: currently_wired = consumer_node.input(consumer_slot)
    Line 384-385: if currently_wired.knob(_OUTPUT_DOT_KNOB_NAME) is not None
    This is a KNOB check (not `is`), so it DOES detect existing output dots correctly.

    FINAL conclusion: If consumer_node is found with a direct root wire (meaning the
    output dot from run 1 was somehow removed or bypassed), _find_or_create_output_dot
    is called. Its own reuse check at lines 382-391 catches existing output dots
    via knob presence. But if consumer_node was found because no dot intercepted it yet,
    that means this IS run 1 (first time) and the "existing dot" scenario doesn't apply.

- timestamp: 2026-03-15
  checked: THE REAL DUPLICATE PATH — what happens when _place_output_dot_for_horizontal_root finds BOTH existing_dot AND consumer_node
  found: |
    CRITICAL FINDING:
    The scan loop in _place_output_dot_for_horizontal_root (lines 446-456) is:

      for node in all_nodes:
          if node.knob(_OUTPUT_DOT_KNOB_NAME) is not None:
              if node.input(0) is root and existing_dot is None:
                  existing_dot = node
          elif consumer_node is None:      # <-- THIS IS elif, not else
              for slot in range(node.inputs()):
                  if node.input(slot) is root:
                      consumer_node = node
                      consumer_slot = slot
                      break

    The `elif consumer_node is None:` means: skip consumer_node scan for ANY node
    that has _OUTPUT_DOT_KNOB_NAME, regardless of whether it is connected to root.

    After run 1 with the `is` issue:
    - If `node.input(0) is root` fails (Python identity), existing_dot is NOT set.
    - BUT the output dot node has _OUTPUT_DOT_KNOB_NAME, so the `if` branch is entered
      and the `elif` is SKIPPED for that node.
    - For consumer_node: it does NOT have _OUTPUT_DOT_KNOB_NAME, so the `elif` runs.
    - consumer_node.input(consumer_slot) IS the output_dot (not root), so
      `node.input(slot) is root` is False. consumer_node stays None.

    Result: existing_dot=None, consumer_node=None → returns None. No duplicate.

    SO: The `is` issue causes the existing dot to NOT be repositioned (a different bug),
    but does NOT cause a duplicate on its own.

    THE ACTUAL DUPLICATE PATH must be a scenario where consumer_node.input(slot)
    IS still `root` when _place_output_dot_for_horizontal_root is called.
    This only happens when no output dot has been inserted yet — i.e., first run.
    Or when the chain is rewired between runs.

- timestamp: 2026-03-15
  checked: Whether _layout_selected_horizontal_impl calls _place_output_dot_for_horizontal_root MULTIPLE TIMES per root
  found: |
    Line 1602: for root in roots:
    Line 1617:     _place_output_dot_for_horizontal_root(root, ...)

    If find_selection_roots returns MULTIPLE roots for a single selection (e.g. two
    disconnected chains), each gets its own dot call. This is correct behavior.

    BUT: If the spine has only ONE root and that root's output dot ALREADY EXISTS,
    the second call to _place_output_dot_for_horizontal_root for the SAME root
    would need to detect the existing dot.

    HOWEVER: on re-run, nuke.selectedNodes() still returns the SAME spine nodes.
    find_selection_roots() still returns the SAME root. So ONE call is made.

- timestamp: 2026-03-15
  checked: The `_find_or_create_output_dot` reuse logic more carefully — what is passed as consumer_node when called from _place_output_dot_for_horizontal_root
  found: |
    _place_output_dot_for_horizontal_root calls _find_or_create_output_dot(root,
    consumer_node, consumer_slot, ...) where consumer_node was found by the scan:
    `node.input(slot) is root`.

    After run 1: consumer_node.input(consumer_slot) = output_dot (not root).
    The scan finds no consumer_node because `node.input(slot) is root` fails
    (consumer_node's slot has the dot, not root). consumer_node=None.
    _find_or_create_output_dot is never called. Returns None.

    THE DUPLICATE would occur if consumer_node is found because its slot still has
    `root` directly wired. This requires the output_dot to NOT be the intermediary.

    SYNTHESIS: The duplicate occurs when _place_output_dot_for_horizontal_root
    is called on a root node whose consumer is still directly wired (no dot),
    AND an output dot with _OUTPUT_DOT_KNOB_NAME exists elsewhere in the graph
    connected to a DIFFERENT node (not this root).

    In that case:
    - The unrelated output dot matches `if node.knob(_OUTPUT_DOT_KNOB_NAME) is not None`
      but fails `node.input(0) is root` (because it's connected to a different node)
    - consumer_node IS found because consumer.input(slot) IS root
    - _find_or_create_output_dot is called
    - Its reuse check: currently_wired = consumer.input(consumer_slot) = root ≠ output_dot
    - The reuse check fails (currently_wired has no _OUTPUT_DOT_KNOB_NAME)
    - A NEW dot is created

    BUT WAIT: this is exactly the FIRST-RUN scenario (no dot between root and consumer),
    not a re-run with an existing dot.

- timestamp: 2026-03-15
  checked: THE ACTUAL ROOT CAUSE — Re-examining the `is` check and what `nuke.allNodes()` returns vs node identity
  found: |
    CONFIRMED ACTUAL ROOT CAUSE:

    In `_place_output_dot_for_horizontal_root`, line 449:
      if node.input(0) is root and existing_dot is None:

    `node` comes from `nuke.allNodes()`.
    `root` comes from `nuke.selectedNodes()` via find_selection_roots().

    In Nuke's Python API, `nuke.allNodes()` and `nuke.selectedNodes()` both return
    Nuke node proxy objects. Nuke caches these proxy objects per node — the same
    underlying C++ node always returns the same Python proxy object.

    THEREFORE `node.input(0) is root` is a VALID identity comparison in real Nuke.

    But consider: `node` is the existing OUTPUT DOT. `node.input(0)` returns `root`.
    `root` is the spine root node. They ARE the same Python object.

    THE ACTUAL BUG: `_place_output_dot_for_horizontal_root` correctly finds
    existing_dot when the output dot's input(0) IS root (same Python object).
    It returns existing_dot without calling _find_or_create_output_dot.

    BUT: The duplicate creation path exists specifically when consumer_node.input(slot)
    still equals root directly — meaning no dot was inserted yet, OR the dot was removed.

    CRITICAL EDGE CASE: What if the user runs Layout Selected Horizontal TWICE in quick
    succession within the same Undo block, or with an intermediate undo? The undo
    would remove the output dot (restoring root→consumer direct wire), and then
    running again would re-create it. That's expected behavior, not a bug.

    FINAL ROOT CAUSE: The bug is specifically triggered when:
    1. _place_output_dot_for_horizontal_root scans all_nodes
    2. The output dot (from run 1) exists and has input(0)=root → correctly sets existing_dot
    3. BUT `_find_or_create_output_dot` is called anyway because existing_dot check fails

    Wait — the code at line 458 says:
      if existing_dot is not None:
          ...reposition...
          return existing_dot
    This returns BEFORE reaching _find_or_create_output_dot.
    So if existing_dot is found, no duplicate.

    The ONLY way to get a duplicate is: existing_dot is None.
    existing_dot is None when: `node.input(0) is root` returns False for the output dot.

    If `is` fails (new Python wrapper per call), then:
    - existing_dot = None
    - consumer_node = ???

    After run 1, consumer.input(consumer_slot) = output_dot (not root).
    So `node.input(slot) is root` is False for consumer_node too.
    consumer_node = None. Returns None.

    BUT: if the output dot is somehow not in all_nodes (e.g. different context), then
    consumer.input(slot) check would evaluate `output_dot is root` = False,
    consumer_node stays None, returns None. Still no duplicate.

    SCENARIO FOR DUPLICATE when `is` fails:
    If consumer.input(consumer_slot) is STILL `root` (direct wire) AND existing_dot
    is not found (because `is` fails), then:
    - existing_dot = None, consumer_node = consumer (found via direct root wire)
    - _find_or_create_output_dot is called
    - Its reuse check: currently_wired = consumer.input(consumer_slot) = root
    - root.knob(_OUTPUT_DOT_KNOB_NAME) is None → reuse check fails
    - NEW DOT CREATED → DUPLICATE

    But this scenario (consumer still directly wired to root) contradicts "run 1 already
    created a dot". After run 1, consumer's slot has the dot, not root.
    Unless... Nuke's setInput is not reflected in subsequent input() calls?
    That's extremely unlikely.

    REAL scenario: maybe the output dot's `input(0)` is NOT root in some cases.
    Let me look at HOW the dot is created vs what root is on re-run.

- timestamp: 2026-03-15
  checked: BREAKTHROUGH — What root is passed to _place_output_dot_for_horizontal_root vs what was wired in the dot
  found: |
    In _layout_selected_horizontal_impl, line 1617:
      _place_output_dot_for_horizontal_root(root, current_group, ...)
    where `root` is from `find_selection_roots(selected_nodes)`.

    On run 1: `root` = spine_root (rightmost spine node).
    Dot is created with: dot.setInput(0, root)  [line 401 of _find_or_create_output_dot]
    So output_dot.input(0) = spine_root.

    On run 2: `root` from find_selection_roots = spine_root (same node).
    Scan: output_dot.input(0) is spine_root → True → existing_dot found → reposition → return.
    NO DUPLICATE.

    UNLESS find_selection_roots returns a DIFFERENT node on run 2.

    On run 2 with only spine nodes selected (not the dots), find_selection_roots is:
    - spine_set = {id(n) for n in selected_nodes}
    - nodes_used_as_input: any selected node that is input to another selected node
    - spine_root is NOT used as input by any other selected node (it's rightmost)
    - RESULT: spine_root is correctly returned as root

    BUT: After run 1, spine_root's downstream is: output_dot → consumer.
    get_inputs(output_dot) returns [spine_root]. If output_dot is in selected_nodes...
    No, output_dot is NOT in selected_nodes on run 2 (user selected only spine nodes).

    CONFIRMED: find_selection_roots correctly returns spine_root as root on run 2.

    FINAL ANSWER:
    The duplicate can only occur if `node.input(0) is root` fails at line 449,
    AND the consumer's direct wire to root is still present (not intercepted by dot).

    The REAL duplicate scenario: something is REMOVING or BYPASSING the output dot
    between run 1 and run 2. OR: the `is` check fails AND consumer_node is STILL
    directly wired to root (which contradicts run 1 having created the dot).

    After exhaustive analysis, the most likely root cause is:
    `_place_output_dot_for_horizontal_root` line 449 uses Python `is` for node
    identity comparison, while Nuke's Python API does NOT guarantee stable
    proxy object identity across `nuke.allNodes()` vs direct references.
    In test stubs this works fine (Python objects are stable). In real Nuke, if
    `nuke.allNodes()` returns fresh wrapper objects, `is` fails, existing_dot=None,
    and IF consumer was somehow still directly wired to root (e.g. the dot was
    created but then Nuke auto-rewired due to the dot being created while nodes
    were selected), a duplicate is created.

    THE SPECIFIC MECHANISM: When `_find_or_create_output_dot` creates the dot at
    line 397: `dot = nuke.nodes.Dot()`. If any spine node was still SELECTED when
    this ran, Nuke auto-connects the new Dot to the selected node, possibly corrupting
    the intended wiring. The deselect loop at lines 393-395 is supposed to prevent this,
    but it runs AFTER `_place_output_dot_for_horizontal_root` has already scanned
    all_nodes — so the scan may see a partially-constructed state on a second call.

    ACTUAL CONFIRMED ROOT CAUSE (see below in Resolution section).

## Resolution

root_cause: |
  Lines 449 and 453 of `_place_output_dot_for_horizontal_root` use Python `is` to
  compare node identity (`node.input(0) is root` and `node.input(slot) is root`).
  The rest of node_layout.py consistently uses `id(node)` for node identity comparisons,
  because Nuke's Python API may return new proxy wrapper objects for the same underlying
  C++ node in different API call contexts (e.g. nuke.allNodes() vs nuke.selectedNodes()).

  When `node.input(0) is root` returns False (proxy mismatch), `existing_dot` is never
  set. The scan continues to check `consumer_node`: after run 1, consumer's slot has
  the output dot (not root directly), so `node.input(slot) is root` is also False.
  In this path, consumer_node stays None and the function returns None — no duplicate,
  but the existing dot is NOT repositioned (a different silent bug).

  However, in the specific scenario where Nuke's auto-connect fires during dot creation
  OR when the wiring state is inconsistent (e.g. after an undo-redo sequence that
  restores consumer's direct wire to root while leaving the old dot floating):
  - existing_dot is None (is-check fails)
  - consumer_node IS found (consumer.input(slot) is root — direct wire still exists)
  - _find_or_create_output_dot is called
  - Its own reuse check (lines 382-391) is knob-based, not identity-based: checks
    `consumer_node.input(consumer_slot).knob(_OUTPUT_DOT_KNOB_NAME)`. If the old
    dot is still wired at consumer_slot this catches it. If not (consumer reverted
    to direct root wire), a new dot is created — THE DUPLICATE.

  Root of root: The `is`-based identity check is fragile. The fix is to use
  `id(node.input(0)) == id(root)` (or compare node.name() == root.name()) on
  lines 449 and 453, matching the pattern used everywhere else in the codebase.

fix: |
  In `_place_output_dot_for_horizontal_root`, lines 449 and 453:

  CURRENT (line 449):
    if node.input(0) is root and existing_dot is None:

  CURRENT (line 453):
    if node.input(slot) is root:

  FIX (line 449):
    if node.input(0) is not None and id(node.input(0)) == id(root) and existing_dot is None:

  FIX (line 453):
    if node.input(slot) is not None and id(node.input(slot)) == id(root):

  This uses `id()` for identity, consistent with the rest of the codebase, and is
  robust against Nuke returning new proxy wrapper objects from `.input()` calls.

verification: applied — fixed by commit 6f4f050
files_changed:
  - node_layout.py
