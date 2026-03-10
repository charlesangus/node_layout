---
created: 2026-03-08T03:11:06.110Z
title: Group View layout commands not scoped to Group
area: general
files:
  - node_layout.py
---

## Problem

Layout commands (`layout_upstream`, `layout_selected`) and `push_nodes_to_make_room` use `nuke.thisGroup()` to capture Group context, but this only works when the user has entered the Group via Ctrl-Enter (fully inside the Group). It does NOT work in "Group View" mode — where the Group's contents are shown inline on the same DAG without the user actually being inside it.

Nuke has a dedicated API function for creating nodes in the correct context in Group View mode; the right call needs to be identified and used in the relevant layout entry points and node creation calls so that Group View behaves the same as Ctrl-Enter.

## Solution

Research the correct Nuke API for Group View context (likely something like `nuke.activeGroup()` or similar). Update `layout_upstream()`, `layout_selected()`, and any `nuke.nodes.Dot()` creation calls to use it so that Dot nodes and push-away are correctly scoped whether the user is inside the Group (Ctrl-Enter) or viewing it via Group View.
