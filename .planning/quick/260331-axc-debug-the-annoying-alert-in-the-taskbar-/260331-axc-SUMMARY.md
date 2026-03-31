---
phase: quick-260331-axc
plan: 01
subsystem: overlay
tags: [windows, activation, taskbar, ctypes, win32]
dependency_graph:
  requires: [node_layout_overlay.py]
  provides: [taskbar-activation-suppression]
  affects: [leader-key-overlay-show]
tech_stack:
  added: [ctypes Win32 API (Windows-only)]
  patterns: [showEvent override, Win32 ctypes guard, no-op on non-Windows]
key_files:
  modified: [node_layout_overlay.py]
decisions:
  - "Use ctypes WS_EX_NOACTIVATE in showEvent rather than relying on Qt flags alone"
  - "Add SetForegroundWindow fallback to restore Nuke focus after activation bleed"
metrics:
  duration: "~5min (continuation from checkpoint)"
  completed: "2026-03-31T15:01:14Z"
  tasks_completed: 1
  files_modified: 1
---

# Phase quick-260331-axc Plan 01: Debug Taskbar Alert — Summary

**One-liner:** Suppressed overlay window activation on Windows via ctypes WS_EX_NOACTIVATE in showEvent, eliminating autohide taskbar reveal and Nuke icon highlight.

## What Was Built

Added two module-level helpers and a `showEvent` override to `LeaderKeyOverlay`:

1. **`_apply_no_activate_win32(hwnd)`** — sets `WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW` on the actual Windows HWND via `SetWindowLongPtrW`, then calls `SetWindowPos` with `SWP_NOACTIVATE | SWP_FRAMECHANGED` to apply the style without triggering further activation

2. **`_restore_nuke_focus(parent_widget)`** — calls `SetForegroundWindow()` on the Nuke parent window as a secondary safeguard in case Windows briefly granted the overlay focus

3. **`LeaderKeyOverlay.showEvent()`** — override that calls both helpers on every show; reliable for first show AND subsequent re-shows (second arm() call and beyond)

Both helpers are no-ops on non-Windows platforms and swallow all exceptions so Nuke never crashes from a cosmetic Win32 failure.

## Root Cause

**Why Qt flags alone were insufficient:**

Qt sets `WS_EX_NOACTIVATE` via `CreateWindowExW` flags at window creation time. However, when the overlay is re-shown after being hidden (the second `arm()` call), Qt calls `ShowWindow(hwnd, SW_SHOW)` without re-creating the native window. On some Windows versions/builds, `ShowWindow()` ignores the existing `WS_EX_NOACTIVATE` flag and activates the window anyway.

This explains why the alert persisted until the overlay window was closed — the first show worked fine (window creation respected the flag), but subsequent shows (after `hide()` + `show()`) activated the window.

## Fix

The `showEvent` override re-asserts `WS_EX_NOACTIVATE` unconditionally on every show, via ctypes, so it applies regardless of whether Qt reset the flag internally.

## Commits

- `93469df` — fix(taskbar-alert): suppress window activation via ctypes Win32 WS_EX_NOACTIVATE in showEvent

## Deviations from Plan

None — implemented exactly the "AUTOHIDE REVEAL" branch from Task 3's action spec.

## Known Stubs

None.

## Self-Check: PASSED

- `node_layout_overlay.py` exists and parses correctly
- `_apply_no_activate_win32` and `_restore_nuke_focus` present as module-level functions
- `showEvent` present in `LeaderKeyOverlay` class
- Commit `93469df` exists in git log
