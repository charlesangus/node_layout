# Coding Conventions

**Analysis Date:** 2026-03-03

## Naming Patterns

**Files:**
- Lowercase with underscores: `node_layout.py`, `make_room.py`, `util.py`
- No special prefixes or suffixes beyond semantic meaning
- Primary entry point for Nuke integration: `menu.py`

**Functions:**
- Public functions use descriptive snake_case: `layout_upstream()`, `layout_selected()`, `collect_subtree_nodes()`, `compute_node_bounding_box()`
- Private/internal functions prefixed with single underscore: `_collect_toolbar_items()`, `_hides_inputs()`, `_is_mask_input()`, `_passes_node_filter()`
- Functions express intent through clear naming without abbreviations (e.g., `vertical_gap_between()` not `v_gap()`)

**Variables:**
- snake_case for all local and module-level variables: `node_filter`, `input_slot_pairs`, `side_margins`, `bottom_y`, `x_positions`
- Loop counters use conventional single letters: `i`, `j`, `n` when iterating over sequences
- Temporary/throwaway variables still use descriptive names (rarely abbreviated): `visited`, `deferred`, `memo`, `nodes_to_move`

**Constants:**
- ALL_CAPS for module-level constants: `SUBTREE_MARGIN = 300`, `MASK_INPUT_MARGIN`, `_TOOLBAR_FOLDER_MAP`, `_MERGE_LIKE_CLASSES`
- Private module constants prefixed with underscore: `_TOOLBAR_FOLDER_MAP`, `_MERGE_LIKE_CLASSES`
- Constants are documented with inline comments explaining their purpose and units

**Types:**
- No type hints used (codebase targets Python 2.7 compatibility for Nuke)
- Data structures documented via docstrings and inline comments
- Function parameters and return types explained in docstrings

## Code Style

**Formatting:**
- 4-space indentation (consistent throughout)
- No line length enforcement observed; lines range from short to 150+ characters
- No formatting tool configuration detected (no `.black`, `.prettierrc`, etc.)

**Linting:**
- No linting tool configuration detected (no `.pylintrc`, `.flake8`, etc.)
- Code follows implicit PEP 8 style with some variation (long lines accepted)

## Import Organization

**Order:**
1. Standard library imports (when used)
2. Third-party Nuke SDK imports: `nuke`, `nukescripts`
3. Local module imports: `node_layout`, `make_room`, `util`

**Pattern Examples:**
```python
# From menu.py
import nuke
import node_layout
import make_room
import util

# From node_layout.py (minimal imports)
import nuke

# From util.py
import nuke
import nukescripts
```

**Path Aliases:**
- Not used; codebase relies on being placed in Nuke's plugin path
- Import statements are relative (e.g., `import node_layout` expects same directory in plugin path)

## Error Handling

**Patterns:**
- Broad exception catching for resilience in Nuke context: `except Exception:` with generic handlers
- Used when interfacing with Nuke preference system which may not have expected knobs
- Example from `get_dag_snap_threshold()`:
```python
def get_dag_snap_threshold():
    try:
        return int(nuke.toNode("preferences")["dag_snap_threshold"].value())
    except Exception:
        return 8  # sensible default when preferences unavailable
```

- Similar pattern in `_is_mask_input()` when checking input labels that may not exist
- No custom exception types; relies on try-except for control flow when accessing dynamic Nuke API

## Logging

**Framework:** console via print() (rarely used)

**Patterns:**
- Minimal logging; only one `print()` statement found in entire codebase (`util.py` line 13)
- No logging framework imported (no logging or print statements in critical paths)
- Plugin operates silently, relying on Nuke's GUI feedback (node repositioning is the output)

## Comments

**When to Comment:**
- Complex algorithms explained with multiline comment blocks before implementation
- Strategic comments on critical sections: Y placement algorithm, diamond resolution strategy, X positioning formulas
- Inline comments for constants explaining units and purpose: `# vertical clearance between adjacent subtrees`
- Comments explain the "why" of complex logic, not the "what" of obvious code

**JSDoc/TSDoc:**
- Not used (Python codebase)
- Docstrings used selectively for complex functions (see below)

**Docstring Pattern:**
- One-line docstrings for simple functions: `"""Return True if node should be included given node_filter."""`
- Multi-line docstrings for complex algorithms with parameters and behavior:
```python
def _reorder_inputs_mask_last(input_slot_pairs, node, all_side):
    """Move mask side inputs to the end so they appear rightmost when n > 2.

    In normal mode (not all_side), input[0] is the primary (above), so only the
    side inputs (index 1+) are reordered.  In all_side mode, every input is a
    side input, so the whole list is reordered.  When n <= 2 there is at most one
    side input so ordering is moot.
    """
```

- Docstrings in `place_subtree()` span sections explaining coordinate system, Y placement algorithm, and X placement separately
- No parameter/return type documentation (relies on docstring text and code clarity)

## Function Design

**Size:**
- Functions range from 2 lines to 140+ lines
- Complex algorithms (e.g., `place_subtree()`, `compute_dims()`) are large but focused on single responsibility
- Helper functions kept small and composable

**Parameters:**
- Prefer explicit parameters over global state when possible
- Pass `memo` dict through call stack for memoization
- Use `node_filter` parameter to constrain graph traversal
- Optional parameters with sensible defaults: `node_filter=None`, `nodes_so_far=None`

**Return Values:**
- Functions return appropriate types: tuples for dimensions `(width, height)`, sets for node IDs, lists of nodes, or None
- Early returns used to handle edge cases (e.g., empty input lists)
- Mutable objects (lists, dicts) may be modified in-place when semantically appropriate

**Recursion:**
- Recursive traversal of node graphs: `_claim()` recursively follows inputs
- Recursive placement: `place_subtree()` recursively positions upstream subtrees
- No explicit depth limit; relies on finite acyclic graph structure of Nuke DAG

## Module Design

**Exports:**
- No `__all__` definition
- Public functions available for direct import and Nuke menu registration
- Nuke menu (`menu.py`) imports and references public functions directly

**Barrel Files:**
- Not used; each module has focused responsibility

**File Organization:**
- `node_layout.py`: Core layout engine (500+ lines) - dimension calculation, placement, diamond resolution, collision avoidance
- `make_room.py`: Bulk node displacement utility (~40 lines)
- `util.py`: Helper utilities (~40 lines) - sorting, upstream selection
- `menu.py`: Nuke integration (~30 lines) - menu registration and command binding

**Initialization:**
- `menu.py` is the entry point, imported by Nuke's plugin system
- Registers commands immediately on module load
- No explicit initialization functions needed

---

*Convention analysis: 2026-03-03*
