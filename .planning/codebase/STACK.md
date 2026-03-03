# Technology Stack

**Analysis Date:** 2026-03-03

## Languages

**Primary:**
- Python 3.x - Core plugin implementation for Nuke

## Runtime

**Environment:**
- Nuke (The Foundry) - Proprietary VFX compositing software that provides the Python runtime environment
- Plugin-based execution within Nuke's embedded Python interpreter

**No external package manager:**
- This is a pure Python plugin with no package dependencies
- All required modules are provided by Nuke's runtime

## Frameworks

**Core:**
- Nuke Python API (nuke module) - Provides access to DAG manipulation, node operations, menu registration, and UI interaction

**Utilities:**
- nukescripts - Nuke utility module used for node selection operations and UI utilities

## Key Dependencies

**Standard Library:**
- No external dependencies beyond Nuke's built-in Python and the nuke/nukescripts modules

**Nuke-Provided:**
- `nuke` - Core Nuke Python API for node graph operations, menu registration, and coordinate manipulation
- `nukescripts` - Nuke utilities for selection management and scripting helpers

## Configuration

**Environment:**
- Nuke plugin path configuration via `init.py`
- Nuke preferences accessed programmatically:
  - `dag_snap_threshold` - Nuke's DAG snap threshold setting used for dynamic spacing calculations
  - Node color preferences (NodeColourSlot, NodeColourChoice) - Accessed from preferences node for color-aware node grouping
  - Node tile_color knob settings - Per-node visual property for same-color node detection

**Build:**
- No build process required
- Pure Python source files deployed directly to Nuke plugin path

## Platform Requirements

**Development:**
- The Foundry Nuke (any recent version supporting Python 3)
- Text editor or Python IDE for editing .py files
- Access to shared network path (optional, for studio-wide installations)

**Production:**
- Nuke installation with Python 3.x support
- Plugin path properly configured in user or studio `~/.nuke/init.py`

---

*Stack analysis: 2026-03-03*
