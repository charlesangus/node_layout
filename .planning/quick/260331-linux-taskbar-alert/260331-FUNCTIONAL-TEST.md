# Task 3: Linux Taskbar Alert Functional Test

## Test Plan

This test verifies that pressing Shift+E to invoke the leader key overlay does NOT trigger taskbar activation on Linux.

### Prerequisites

1. Linux system (X11 or Wayland) with autohide taskbar/dock enabled
   - GNOME: Settings > Dock > Auto-hide Dock
   - KDE: Right-click panel > Configure panel > Auto-hide

2. Nuke with node_layout plugin loaded

3. Nuke window in windowed mode (not maximized) for clearer taskbar behavior observation

### Test Steps

1. Open Nuke and confirm the plugin is loaded (check Menu > Linux layout tools if available)

2. Position the Nuke window so the taskbar/dock is visible

3. Press **Shift+E** to invoke the leader key overlay

4. Observe the following:
   - [ ] Taskbar/dock does NOT slide out or reveal itself
   - [ ] Nuke taskbar icon does NOT highlight or flash
   - [ ] Leader key overlay appears at cursor position
   - [ ] Keyboard focus remains in DAG panel (typing works after dismissing overlay)

5. Dismiss the overlay by pressing Escape

6. Repeat steps 3-5 two more times to confirm consistent behavior (re-show should not trigger alert)

### Expected Results

All observations should confirm:
- No taskbar reveal/autohide trigger
- No icon highlighting or flashing
- Overlay appears and disappears cleanly
- DAG panel retains keyboard focus throughout

### Code Changes Tested

1. **_apply_linux_hints()** - Sets X11/Wayland skip-taskbar and skip-pager properties
2. **show() method** - Uses setGeometry() instead of move() on Linux to avoid ConfigureNotify events
3. **showEvent() method** - Restores focus to parent window on Linux using raise() and activateWindow()

### Diagnosis (if test fails)

If taskbar alert still occurs, run on the Linux system:

```bash
xprop -id $(xdotool search --name "LeaderKeyOverlay") _NET_WM_WINDOW_TYPE _NET_WM_STATE
```

This will show whether the X11 window hints are being properly applied by the window manager.

## Test Status

Manual functional test — requires Linux system with Nuke to execute fully.
Code verification confirms all required changes are in place.
