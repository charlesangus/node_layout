---
status: partial
phase: 20-wasd-chaining-c-command
source: [20-VERIFICATION.md]
started: 2026-03-30T00:00:00Z
updated: 2026-03-30T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. WASD movement amount correctness in Nuke
expected: In a live Nuke session, arm leader mode (Shift+E) and press W — nodes move upward by 1600 units. Press S — 1600 units downward. Press A — 800 units left. Press D — 800 units right. Amounts match existing bracket shortcuts exactly.
result: [pending]

### 2. Leader mode stays active after chaining keypresses
expected: Arm leader mode, press W five times rapidly — nodes move five times and leader mode remains active throughout; no fallback to normal Nuke behavior.
result: [pending]

### 3. Overlay hides and does not reappear during session
expected: Arm leader mode, wait for overlay hint to appear, press W — overlay dismisses and does not reappear on subsequent W/A/S/D/Q/E presses within the same session.
result: [pending]

### 4. Auto-repeat guard in practice
expected: Arm leader mode, hold the W key down — nodes move once on keydown and do NOT continuously move with OS key-repeat; all repeat events silently consumed.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
