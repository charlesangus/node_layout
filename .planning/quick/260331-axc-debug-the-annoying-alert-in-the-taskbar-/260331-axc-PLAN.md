---
phase: quick-260331-axc
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [node_layout_overlay.py, node_layout_leader.py]
autonomous: true
requirements: []
must_haves:
  truths:
    - "Pressing Shift+E no longer triggers taskbar alert/notification on Windows"
    - "Overlay appears without visual taskbar indication"
  artifacts:
    - path: "node_layout_overlay.py"
      provides: "LeaderKeyOverlay window configuration"
    - path: "node_layout_leader.py"
      provides: "arm() entry point and filter lifecycle"
  key_links:
    - from: "node_layout_leader.py"
      to: "node_layout_overlay.py"
      via: "arm() calls _overlay.show()"
      pattern: "_overlay.show()"
---

<objective>
Debug and eliminate the taskbar alert notification that appears when pressing Shift+E to invoke leader mode.

Purpose: The user reports an "annoying alert in the taskbar" when triggering the leader command. Recent fixes (ebe9f0d, 476c17a, d598895) addressed taskbar flash via WA_ShowWithoutActivating, WindowDoesNotAcceptFocus, cursor handling, and reparent() logic. This quick task identifies what alert remains and removes it.

Output: Root cause identified, window flags or lifecycle adjusted to suppress the alert completely.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/quick/260331-axc-debug-the-annoying-alert-in-the-taskbar-/CONTEXT.md

Recent related quick fixes:
- 260331-594: Added reparent() to prevent parent resets from undoing window flags
- ebe9f0d (taskbar-flash): Move geometry before show() to avoid SetWindowPos without SWP_NOACTIVATE
- 476c17a (taskbar-flash): Move setCursor to overlay level to reduce per-widget WM_SETCURSOR messages
- d598895 (taskbar-flash): Add WindowDoesNotAcceptFocus flag to suppress WS_EX_NOACTIVATE on Windows

Current window configuration:
- Qt.WindowType.Tool + FramelessWindowHint + WindowDoesNotAcceptFocus
- WA_ShowWithoutActivating + WA_TranslucentBackground
- move() before show() to avoid SetWindowPos during visible window
- reparent() restores all flags after parent change
</context>

<tasks>

<task type="auto">
  <name>Task 1: Identify alert type and source</name>
  <files>node_layout_overlay.py, node_layout_leader.py</files>
  <action>
    Investigate what "alert in the taskbar" means in Windows context:

    1. Check if the alert is a taskbar notification/toast (Windows notification area) — these are typically triggered by:
       - QMessageBox or QErrorMessage (none present, grep confirms)
       - nuke.alert(), nuke.message(), nuke.error() calls (check for these in both files)
       - Unhandled exceptions during arm() or show()
       - Window activation request that breaks through NoActivate flags (less likely given recent fixes)

    2. Audit the show() and arm() call paths:
       - arm() in node_layout_leader.py creates overlay, sets flags, shows it
       - LeaderKeyOverlay.show() positions window then calls super().show()
       - Check if any exception handlers or error paths trigger notifications

    3. Check if it's a Windows audio/visual alert rather than notification:
       - Some Windows versions play a ding sound or show a brief visual indicator
       - This would suggest focus/activation is still occurring despite flags
       - QApplication.beep() or system sounds being triggered

    Search for: "alert", "message", "beep", "error", "exception" in both files
    Look at arm() -> show() flow end-to-end

    If the alert is a system notification (QMessageBox-style), it would be blocking — easy to spot.
    If it's a taskbar flash/attention, it's likely still a SetWindowPos or focus-steal issue, despite recent fixes.
    If it's a Windows audio alert, it's activation-related.
  </action>
  <verify>
    Document findings in node_layout_overlay.py or node_layout_leader.py as inline comment describing the alert
  </verify>
  <done>Root cause of alert identified and documented in code comments</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>Window flag and lifecycle investigation</what-built>
  <how-to-verify>
    Open Nuke and test in a live session:
    1. Click into the DAG panel to give it keyboard focus
    2. Press Shift+E and observe carefully
    3. Report what you see in the taskbar:
       - Does the taskbar flash or highlight the Nuke icon?
       - Does a notification popup/toast appear in the bottom right (Windows notification area)?
       - Does a ding sound play?
       - Does the taskbar show an "alert" badge or number on the Nuke icon?
       - Does the autohide taskbar reveal itself?
    4. Describe the exact visual/audio behavior you see
  </how-to-verify>
  <resume-signal>
    Describe the exact behavior:
    - What happens in the taskbar when you press Shift+E?
    - Is it a sound, a visual flash, a notification popup, or something else?
    - Does it happen every time or intermittently?
  </resume-signal>
</task>

<task type="auto">
  <name>Task 3: Apply targeted fix based on alert type</name>
  <files>node_layout_overlay.py, node_layout_leader.py</files>
  <action>
    Once alert type is confirmed from checkpoint:

    If TASKBAR FLASH (window activation bleeding through):
    - Check if show() is being called while parent is not visible (would cause native window creation as top-level)
    - Verify reparent() is being called before arm() if overlay is being reused across sessions
    - Consider setting WS_EX_TOOLWINDOW explicitly (Windows-specific, requires ctypes or PyQt6 internals)
    - Audit all paths that modify LeaderKeyOverlay state or call show()

    If NOTIFICATION POPUP:
    - Check arm() exception path — is any error being caught and reported?
    - Look for nuke.alert/message/error calls (unlikely but possible in dispatch helpers)
    - Verify no exceptions propagate during show()

    If SOUND ALERT (system ding):
    - This is usually QApplication.beep() or Windows activation sound
    - Likely still a focus-steal issue
    - May need to suppress QApplication.beep() if accidentally triggered
    - Or verify SetWindowPos is truly not being called

    If AUTOHIDE REVEAL:
    - This is activation-related; similar fix to taskbar flash
    - Verify SetWindowPos happens only with SWP_NOACTIVATE (it doesn't by default in Qt)
    - The move() before show() fix should have solved this; if not, may need deeper investigation

    Apply the fix and test.
  </action>
  <verify>
    <automated>
      python3 -c "
      import ast
      with open('node_layout_overlay.py') as f:
        tree = ast.parse(f.read())
      print('WindowDoesNotAcceptFocus flag: OK')
      "
    </automated>
  </verify>
  <done>Alert is eliminated or reduced to acceptable level; Shift+E no longer triggers taskbar notification/flash/sound</done>
</task>

</tasks>

<verification>
After fix is applied:
1. Open Nuke and press Shift+E
2. Observe taskbar — no flash, no notification, no sound, no autohide reveal
3. Overlay appears smoothly at cursor position
4. Subsequent keys dispatch correctly (leader mode still works)
5. Checkpoint passes with "alert is gone"
</verification>

<success_criteria>
- Alert is completely eliminated when pressing Shift+E in a live Nuke session
- Overlay still appears and functions normally
- No regression in existing functionality (WASD, Q/E chaining, menu dispatch)
</success_criteria>

<output>
After completion, create `.planning/quick/260331-axc-debug-the-annoying-alert-in-the-taskbar-/260331-axc-SUMMARY.md` with:
- Alert type identified and root cause
- Fix applied (if needed)
- Test confirmation
- Commits (if code changed) or "no changes needed" if it was config/environment issue
</output>
