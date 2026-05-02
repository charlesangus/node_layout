"""Safe Delete -- replacement for Nuke's default node delete behaviour.

Nuke's stock delete prompts about broken hidden-input and expression links even
when every dependent of the deleted node is also being deleted in the same
operation. That noise trains users to click through the prompt, which defeats
the warning entirely.

Safe Delete only prompts when a deleted node has dependents that are NOT also
being deleted -- i.e. when the operation would actually leave a dangling link.
The Viewer node is always treated as a benign dependent.

Installed by `menu.py` via `install()`, which monkey-patches
`nukescripts.node_delete` so the standard Backspace/Delete shortcut routes here.
The original delete callable is captured at install time so the
``safe_delete_enabled`` preference can fall back to stock behaviour at runtime.
"""

import inspect
import re

import nuke
import nukescripts

import node_layout_prefs

_DEPENDENCY_TYPES = {
    "Hidden Input": nuke.HIDDEN_INPUTS,
    "Expression": nuke.EXPRESSIONS,
}

# Captured by install() so the disabled branch can defer to whatever
# ``nukescripts.node_delete`` was before we monkey-patched it.
_original_node_delete = None


def _natural_sort_key(text):
    """Sort key that orders ``Read1, Read2, Read10`` instead of ``1, 10, 2``."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", text)]


def _collect_external_dependents(selected_nodes, evaluate_all):
    """Return a mapping of selected-node-name to {dep-type: [external-dep-names]}.

    Only dependents that are NOT in ``selected_nodes`` (and are not Viewers) are
    recorded. An empty result means the delete is safe.
    """
    selected_set = set(selected_nodes)
    external_dependents = {}

    for node in selected_nodes:
        for dep_type_name, dep_type_flag in _DEPENDENCY_TYPES.items():
            dependent_nodes = nuke.dependentNodes(dep_type_flag, node, evaluateAll=evaluate_all)
            for dependent in dependent_nodes:
                if dependent.Class() == "Viewer":
                    continue
                if dependent in selected_set:
                    continue
                node_bucket = external_dependents.setdefault(node.fullName(), {})
                node_bucket.setdefault(dep_type_name, []).append(dependent.fullName())

    return external_dependents


def _build_warning_html(external_dependents):
    """Render the dependent-link summary used in the confirmation dialog."""
    rows_html = ""
    for node_name in sorted(external_dependents.keys(), key=_natural_sort_key):
        rows_html += (
            "<hr><table cellpadding=0 cellspacing=0>"
            f"<tr><td colspan=4><b>{node_name}</b></td></tr>"
        )
        for dep_type_name, dependent_names in external_dependents[node_name].items():
            for dependent_name in dependent_names:
                rows_html += (
                    "<tr>"
                    "<td width=50>&nbsp;</td>"
                    f"<td width=90>({dep_type_name})</td>"
                    "<td>&nbsp;&nbsp;<span style='font-size:large'>&#x2192;</span>&nbsp;&nbsp;</td>"
                    f"<td>{dependent_name}</td>"
                    "</tr>"
                )
        rows_html += "</table>"
    return rows_html


def _confirm_break_dependencies(external_dependents):
    """Show the modal warning. Return True if the user accepts the deletion."""
    rows_html = _build_warning_html(external_dependents)

    prompt = nukescripts.PythonPanel()
    prompt.setMinimumSize(500, min(1000, 60 + rows_html.count("</tr>") * 24))
    prompt.addKnob(
        nuke.Text_Knob(
            "",
            "",
            "<center><br>Deleting these nodes will break the following dependencies.</center>",
        )
    )
    prompt.addKnob(nuke.Text_Knob("", "", rows_html))
    return bool(prompt.showModalDialog())


def safe_delete(evaluate_all=False):
    """Delete the current selection, prompting only on truly broken dependencies.

    ``evaluate_all`` is forwarded to ``nuke.dependentNodes`` -- set True only if
    expression dependencies should be discovered by evaluating every knob, which
    is expensive on large scripts.
    """
    selected_nodes = nuke.selectedNodes()
    if not selected_nodes:
        nuke.nodeDelete()
        return

    external_dependents = _collect_external_dependents(selected_nodes, evaluate_all)

    if external_dependents and not _confirm_break_dependencies(external_dependents):
        return

    nuke.nodeDelete()


def _call_original_node_delete(popup_on_error, evaluate_all):
    """Forward to the captured stock callable, tolerating signature differences.

    Older Nuke builds expose ``nukescripts.node_delete(popupOnError=False)`` with
    no ``evaluateAll`` parameter; newer builds add it. Passing an unknown kwarg
    blows up at runtime, so we introspect and forward only what the target
    actually declares.
    """
    if _original_node_delete is None:
        nuke.nodeDelete()
        return

    candidate_kwargs = {"popupOnError": popup_on_error, "evaluateAll": evaluate_all}
    try:
        accepted_parameters = inspect.signature(_original_node_delete).parameters
    except (TypeError, ValueError):
        # Builtins / C-implemented callables: signature() may fail. Fall back to
        # the no-arg form, which always matches the keyboard-shortcut path.
        _original_node_delete()
        return

    forwarded_kwargs = {
        name: value
        for name, value in candidate_kwargs.items()
        if name in accepted_parameters
    }
    _original_node_delete(**forwarded_kwargs)


# Compatibility alias matching the signature `nukescripts.node_delete` expects.
def node_delete(popupOnError=False, evaluateAll=False):  # noqa: N803 -- Nuke API name
    if not node_layout_prefs.prefs_singleton.get("safe_delete_enabled"):
        _call_original_node_delete(popupOnError, evaluateAll)
        return
    safe_delete(evaluate_all=evaluateAll)


def install():
    """Replace the built-in node-delete callable so Backspace/Delete uses Safe Delete.

    Idempotent: re-running install() will not chain wrappers -- the original
    ``nukescripts.node_delete`` captured on the first call is preserved so the
    disabled branch always falls back to true stock behaviour.
    """
    global _original_node_delete
    if _original_node_delete is None:
        _original_node_delete = nukescripts.node_delete
    nukescripts.node_delete = node_delete
