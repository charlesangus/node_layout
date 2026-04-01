# Quick Task 260401-y8p: Rename "Sort by Filename" to "Arrange by Filename"

## Summary
Renamed the "Sort By Filename" menu command to "Arrange by Filename" and repositioned it next to the other arrange commands in the Node Layout menu.

## Changes Made

### menu.py
- Renamed command from "Sort By Filename" to "Arrange by Filename"
- Moved command from separate section to "Arrange" section (lines 115-127)
- Placed immediately after "Arrange Vertical" command
- Preserved function call to `node_layout_util.sort_by_filename()`
- Preserved keyboard shortcut context

## Files Modified
- `menu.py`: 1 edit (rename + reposition)

## Commits
- `f7d2e4f`: chore: rename "Sort by Filename" to "Arrange by Filename" and place in arrange section

## Status
✓ Completed
