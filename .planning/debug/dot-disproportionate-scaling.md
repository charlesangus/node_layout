---
status: investigating
trigger: "Investigate why Dot nodes on secondary/mask inputs move disproportionately (more than other nodes) when shrink/expand scaling commands run"
created: 2026-03-05T00:00:00Z
updated: 2026-03-05T00:00:00Z
symptoms_prefilled: true
goal: find_root_cause_only
---

## Current Focus

hypothesis: "Dot nodes use top-left xpos/ypos, but the scaling anchor also uses xpos/ypos. The dot's visual center is offset from its xpos by half its width (6px). When the layout algorithm positions a side-input dot, it centers it horizontally over the upstream node using: dot_center_x = x_positions[i] + actual_upstream.screenWidth() // 2; dot.setXpos(dot_center_x - dot.screenWidth() // 2). This means the dot's xpos is NOT at the same column as a regular node at x_positions[i] — it is shifted right by roughly (upstream_node_width - dot_width)/2. The scaling formula computes dx = node.xpos() - anchor_x from top-left positions, so the larger raw offset of the dot gets multiplied, resulting in disproportionate movement."
test: "trace through concrete example with numbers"
expecting: "Dot displacement after scaling differs from a regular node at the same logical column"
next_action: "complete root cause write-up with line references"

## Symptoms

expected: "All nodes (including Dots) move proportionally to their logical position relative to the anchor when scaling"
actual: "Dot nodes move disproportionately — more in both shrink and expand, with horizontal movement being the most visible"
errors: "none — wrong output, not a crash"
reproduction: "run shrink_selected / expand_selected / shrink_upstream / expand_upstream with a layout that includes side-input or mask-input Dot nodes"
started: "inherent to design — any time Dots are present"

## Eliminated

- hypothesis: "some other code path repositions Dots separately"
  evidence: "_scale_selected_nodes and _scale_upstream_nodes iterate all nodes uniformly with the same dx/dy formula; no special Dot handling"
  timestamp: 2026-03-05T00:00:00Z

## Evidence

- timestamp: 2026-03-05T00:00:00Z
  checked: "_scale_selected_nodes lines 696-709 and _scale_upstream_nodes lines 712-723"
  found: "Both use anchor_node.xpos() / anchor_node.ypos() (top-left) and compute dx = node.xpos() - anchor_x, dy = node.ypos() - anchor_y using each node's own top-left corner"
  implication: "All nodes are treated identically — top-left offset from anchor, scaled uniformly"

- timestamp: 2026-03-05T00:00:00Z
  checked: "place_subtree Dot placement, lines 471-479"
  found: "Side-input Dots are positioned by: dot_center_x = x_positions[i] + actual_upstream.screenWidth() // 2; dot.setXpos(dot_center_x - dot.screenWidth() // 2); The dot's xpos is therefore (upstream_x + (upstream_width - dot_width) / 2), which is the upstream node's center minus half the dot's tiny width. For a typical 80-wide upstream node and 12-wide dot: dot.xpos() = upstream_x + (80-12)//2 = upstream_x + 34. The upstream node is at upstream_x. After scaling both by the same dx multiplier, the dot's dx (which includes the +34 centering offset) scales along with the true layout offset, stretching the centering shift."
  implication: "The centering offset baked into the dot's xpos gets scaled along with the true layout spacing. This inflates the dot's horizontal movement."

- timestamp: 2026-03-05T00:00:00Z
  checked: "place_subtree Dot Y placement, lines 472-479"
  found: "Bottom-most dot Y: dot_y = y + (node.screenHeight() - inp.screenHeight()) // 2. This centers the dot vertically beside its consumer. For a 26-tall consumer node and 12-tall dot: dot_y = consumer_y + 7. The dot's ypos sits 7 pixels below the consumer's top edge — effectively at the consumer's vertical midpoint. When the anchor is the consumer (the lowest-ypos node), dy = dot_y - anchor_y = 7, a tiny positive number, meaning the dot barely moves vertically (it is nearly at anchor height). That matches the reported symptom that horizontal movement is the bigger problem."
  implication: "Vertical disproportionality is minor for bottom-most dots (small dy). Horizontal disproportionality is the main visible issue."

- timestamp: 2026-03-05T00:00:00Z
  checked: "anchor selection in _scale_selected_nodes line 700"
  found: "anchor_node = max(selected_nodes, key=lambda n: n.ypos()) — uses top-left ypos to pick lowest node on screen. Dot's ypos may place it below the actual consumer if placed with the centering formula."
  implication: "If a Dot's ypos is slightly lower than the consumer's ypos (e.g. dot_y = consumer_y + 7), the Dot could become the anchor itself. Then the consumer is above the anchor and its dy is negative, which is unusual but not the primary reported symptom."

## Resolution

root_cause: |
  The scaling functions (_scale_selected_nodes and _scale_upstream_nodes) treat every
  node's xpos/ypos as a pure layout coordinate and scale the raw top-left offset from
  the anchor. For regular nodes xpos reflects the intended layout column directly.
  For Dot nodes, however, place_subtree embeds a centering correction into xpos:

      dot.setXpos(dot_center_x - dot.screenWidth() // 2)
      where dot_center_x = x_positions[i] + actual_upstream.screenWidth() // 2

  This means the dot's stored xpos already includes half the upstream node's width as
  an intra-cell centering offset (typically +34 px for an 80-wide upstream node with a
  12-wide dot). When the scaling formula computes dx = dot.xpos() - anchor_x, that
  centering offset is part of dx and gets multiplied by the scale factor along with the
  true inter-node spacing. After scaling, the dot is no longer centered over its upstream
  node — it has drifted further right (on expand) or closer to center (on shrink) than
  the upstream node moved.

  The same issue exists in Y for staggered (non-bottom-most) dots:

      dot_y = y_positions[i] + actual_upstream.screenHeight() + _subtree_margin(...)

  The stagger offset is also baked into ypos and scaled, moving the dot out of its
  intended vertical relationship with the upstream node.

  For the bottom-most dot the Y effect is minor because:
      dot_y = consumer_y + (consumer_height - dot_height) // 2  (~7 px above anchor)
  which gives a nearly-zero dy, leaving vertical displacement approximately correct.

fix: |
  Scale nodes relative to their visual center, not their top-left corner. This removes
  the node-size-dependent centering offset from dx/dy before scaling:

      node_center_x = node.xpos() + node.screenWidth() / 2
      node_center_y = node.ypos() + node.screenHeight() / 2
      anchor_center_x = anchor_node.xpos() + anchor_node.screenWidth() / 2
      anchor_center_y = anchor_node.ypos() + anchor_node.screenHeight() / 2

      dx = node_center_x - anchor_center_x
      dy = node_center_y - anchor_center_y

      new_center_x = anchor_center_x + dx * scale_factor
      new_center_y = anchor_center_y + dy * scale_factor

      node.setXpos(int(new_center_x - node.screenWidth() / 2))
      node.setYpos(int(new_center_y - node.screenHeight() / 2))

  Because a Dot's center is at xpos + 6 and a regular node's center is at xpos + 40
  (for an 80-wide node), computing offsets center-to-center cancels the centering
  correction embedded in the dot's xpos, making all nodes scale uniformly relative
  to the anchor regardless of their physical size.

files_changed: []
