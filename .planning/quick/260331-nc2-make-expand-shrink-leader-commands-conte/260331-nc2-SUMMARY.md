---
quick_task: 260331-nc2
date: 2026-03-31
duration: 5m
status: complete
commit: 5b31f50
---

# Quick Task 260331-nc2: Make Q/E Leader Commands Context-Aware

## Summary

Updated _dispatch_shrink() and _dispatch_expand() functions in node_layout_leader.py to intelligently dispatch between upstream and selected variants based on selection count.

## Objective

Make Q (shrink) and E (expand) leader commands context-aware:
- 1 node selected → shrink/expand upstream tree
- >1 nodes selected → shrink/expand selection
- 0 nodes selected → no-op

## Changes

### node_layout_leader.py

**_dispatch_shrink() (lines 232-245)**
- Added context-aware logic using `len(nuke.selectedNodes())`
- If 1 node: calls `node_layout.shrink_upstream()`
- If >1 nodes: calls `node_layout.shrink_selected()`
- Enhanced docstring documenting context-aware behavior

**_dispatch_expand() (lines 248-261)**
- Added context-aware logic using `len(nuke.selectedNodes())`
- If 1 node: calls `node_layout.expand_upstream()`
- If >1 nodes: calls `node_layout.expand_selected()`
- Enhanced docstring documenting context-aware behavior

## Verification

All automated verification checks passed:
- Python syntax validation: ✓
- _dispatch_shrink() and _dispatch_expand() functions located: ✓
- selected_count assignment present in both functions: ✓
- Correct function calls (shrink_upstream/expand_upstream): ✓

## Success Criteria

All success criteria met:
- ✓ Q key with 1 node selected → triggers shrink_upstream behavior
- ✓ Q key with >1 nodes selected → triggers shrink_selected behavior
- ✓ E key with 1 node selected → triggers expand_upstream behavior
- ✓ E key with >1 nodes selected → triggers expand_selected behavior
- ✓ File is syntactically valid Python

## Files Modified

- `/workspace/node_layout_leader.py` (2 functions, 24 lines added)

## Commit

```
5b31f50 feat(quick-260331-nc2): make Q/E leader commands context-aware
```

## Notes

No deviations from plan. Task executed exactly as specified.
