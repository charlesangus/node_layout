"""Pure-Python A/B/C harness: run every layout scenario through every
registered engine and emit position diffs.

Usage::

    pytest tests/compare_engines.py -v
        # writes tests/output/compare_*.json and tests/output/compare_summary.csv
        # one row per (scenario, engine) with bbox area, max-Δ-from-legacy, dot count

    python3 tests/compare_engines.py             # standalone
    python3 tests/compare_engines.py --html      # also emit ascii-grid HTML
    python3 tests/compare_engines.py --engines legacy,bbox

Discovery: scenarios are dictionaries returned by helpers in
``tests/freeze_test_scenarios.py`` plus inline scenarios defined in this
file. Each scenario builds a stub-Nuke graph, names a root, and specifies
which entry point to call (layout_upstream / layout_selected /
layout_selected_horizontal).

Engine selection: each engine name is set via the ``NODE_LAYOUT_ENGINE``
env var before the layout call. Because ``node_layout_engine.get_engine``
reads that env var live, no reimport is needed — the same module-level
``layout_upstream`` reroutes per call.

This file ships as a skeleton on the base branch (legacy only). Each
implementing branch (bbox, shape) extends ``ENGINES`` and re-runs the
harness. The harness will silently skip engines that are not registered
in the current checkout, so the same file works across all three
worktrees.
"""
from __future__ import annotations

import csv
import json
import os
import pathlib
import sys
import time
import unittest
from typing import Any

# Ensure the workspace root is on sys.path so node_layout, nuke stubs etc.
# resolve when running standalone.
_WORKSPACE = pathlib.Path(__file__).resolve().parent.parent
if str(_WORKSPACE) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE))


_OUTPUT_DIR = _WORKSPACE / "tests" / "output"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Engine registry — names appear here regardless of whether they are
# registered in node_layout_engine; missing engines are skipped at run time.
# ---------------------------------------------------------------------------
ENGINES = ["legacy", "bbox", "shape"]


def _engine_available(name: str) -> bool:
    """Return True if the named engine is callable in this checkout.

    'legacy' is always available. Other engines must be registered with
    node_layout_engine via the @register decorator, which happens at
    module import of node_layout_v2_<name>.
    """
    if name == "legacy":
        return True
    # Install stub Nuke before the engine module imports it.
    from tests import _compare_stub_nuke as stubs
    stubs.install_nuke_stub()
    try:
        if name == "bbox":
            import node_layout_v2_bbox  # noqa: F401
        elif name == "shape":
            import node_layout_v2_shape  # noqa: F401
        else:
            return False
    except ImportError:
        return False
    import node_layout_engine
    return name in node_layout_engine.list_registered_engines()


# ---------------------------------------------------------------------------
# Scenario loader — for now, a stub. The real implementation pulls from
# tests/freeze_test_scenarios.py and any other scenario builders. Each
# scenario must return a dict with keys: name, build (callable that
# returns root + selected list), command (str).
#
# Subagents implementing bbox/shape are expected to extend this list with
# scenarios covering vertical, horizontal, freeze, diamond, mask, fan.
# ---------------------------------------------------------------------------
def discover_scenarios() -> list[dict[str, Any]]:
    """Return scenario dicts.

    Each scenario looks like::

        {
            "name": "vertical_chain",
            "build": <callable returning (root_node, selection_list, universe)>,
            "command": "layout_upstream",  # or layout_selected / layout_selected_horizontal
            "scheme_multiplier": None,
        }

    Builders come from ``tests/_compare_stub_nuke.py``; each one constructs a
    fresh stub-Nuke ``Universe`` and registers it. The harness installs the
    stub Nuke before importing node_layout so the recursion uses these stub
    nodes.
    """
    # Defer import: _compare_stub_nuke installs a stub `nuke` module side-effect.
    from tests import _compare_stub_nuke as stubs

    scenarios = []
    for name, builder in stubs.SCENARIO_BUILDERS.items():
        # All scenarios use layout_upstream; horizontal mode is picked up via
        # the stored node_layout_state mode knob, not a different command.
        scenarios.append({
            "name": name,
            "build": builder,
            "command": "layout_upstream",
            "scheme_multiplier": None,
        })
    return scenarios


# ---------------------------------------------------------------------------
# Per-engine runner. Sets NODE_LAYOUT_ENGINE, builds scenario, runs,
# captures positions.
# ---------------------------------------------------------------------------
def run_one(scenario: dict[str, Any], engine: str) -> dict[str, Any]:
    """Run one scenario under one engine and return a result dict."""
    os.environ["NODE_LAYOUT_ENGINE"] = engine
    try:
        # Install stub Nuke FIRST so `import nuke` inside node_layout binds to it.
        from tests import _compare_stub_nuke as stubs
        stubs.install_nuke_stub()

        # Build scenario AFTER stub is in sys.modules; the builder calls into
        # the stub helpers and registers a fresh universe.
        root, selection, universe = scenario["build"]()
        stubs.set_universe(universe)
        # Re-register selection now that universe is the active one.
        if selection:
            universe.select(*selection)

        # Import node_layout the same way as tests do (via importlib spec).
        import importlib
        import importlib.util
        if "node_layout_prefs" not in sys.modules:
            prefs_spec = importlib.util.spec_from_file_location(
                "node_layout_prefs",
                str(_WORKSPACE / "node_layout_prefs.py"),
            )
            prefs_mod = importlib.util.module_from_spec(prefs_spec)
            prefs_spec.loader.exec_module(prefs_mod)
            sys.modules["node_layout_prefs"] = prefs_mod
        if "node_layout_state" not in sys.modules:
            state_spec = importlib.util.spec_from_file_location(
                "node_layout_state",
                str(_WORKSPACE / "node_layout_state.py"),
            )
            state_mod = importlib.util.module_from_spec(state_spec)
            state_spec.loader.exec_module(state_mod)
            sys.modules["node_layout_state"] = state_mod
        if "node_layout_engine" not in sys.modules:
            eng_spec = importlib.util.spec_from_file_location(
                "node_layout_engine",
                str(_WORKSPACE / "node_layout_engine.py"),
            )
            eng_mod = importlib.util.module_from_spec(eng_spec)
            eng_spec.loader.exec_module(eng_mod)
            sys.modules["node_layout_engine"] = eng_mod
        if "node_layout" not in sys.modules:
            nl_spec = importlib.util.spec_from_file_location(
                "node_layout", str(_WORKSPACE / "node_layout.py"),
            )
            nl_mod = importlib.util.module_from_spec(nl_spec)
            nl_spec.loader.exec_module(nl_mod)
            sys.modules["node_layout"] = nl_mod
        node_layout = sys.modules["node_layout"]

        command = scenario["command"]
        scheme_multiplier = scenario.get("scheme_multiplier")

        start = time.perf_counter()
        if command == "layout_upstream":
            node_layout.layout_upstream(scheme_multiplier=scheme_multiplier)
        elif command == "layout_selected":
            node_layout.layout_selected(scheme_multiplier=scheme_multiplier)
        elif command == "layout_selected_horizontal":
            node_layout.layout_selected_horizontal(scheme_multiplier=scheme_multiplier)
        elif command == "layout_selected_horizontal_place_only":
            node_layout.layout_selected_horizontal_place_only(
                scheme_multiplier=scheme_multiplier
            )
        else:
            raise ValueError(f"Unknown command: {command}")
        elapsed = time.perf_counter() - start

        positions = _collect_positions(universe)
        bbox = _bbox_of(positions)
        overlaps = stubs.find_overlapping_node_pairs(universe)
        return {
            "engine": engine,
            "scenario": scenario["name"],
            "positions": positions,
            "bbox": bbox,
            "overlaps": overlaps,
            "elapsed_s": elapsed,
            "ok": True,
        }
    except Exception as e:  # noqa: BLE001
        import traceback
        return {
            "engine": engine,
            "scenario": scenario["name"],
            "error": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc(),
            "ok": False,
        }
    finally:
        os.environ.pop("NODE_LAYOUT_ENGINE", None)


def _collect_positions(universe) -> dict[str, dict]:
    """Record xpos/ypos for every node in the universe."""
    out = {}
    for n in universe.nodes:
        out[n.name()] = {
            "xpos": n.xpos(),
            "ypos": n.ypos(),
            "class": n.Class(),
            "width": n.screenWidth(),
            "height": n.screenHeight(),
        }
    return out


def _bbox_of(positions: dict[str, dict]) -> tuple[int, int, int, int] | None:
    if not positions:
        return None
    xs = [p["xpos"] for p in positions.values()]
    ys = [p["ypos"] for p in positions.values()]
    return (min(xs), min(ys), max(xs), max(ys))


# ---------------------------------------------------------------------------
# Diff/report
# ---------------------------------------------------------------------------
def diff_against_legacy(results: list[dict]) -> dict[str, Any]:
    """Return a diff-summary dict comparing each engine to legacy."""
    by_scenario: dict[str, dict[str, dict]] = {}
    for r in results:
        by_scenario.setdefault(r["scenario"], {})[r["engine"]] = r

    summary: dict[str, Any] = {}
    for scenario, engines in by_scenario.items():
        legacy = engines.get("legacy")
        scenario_summary = {}
        for engine, r in engines.items():
            if not r.get("ok"):
                scenario_summary[engine] = {"error": r.get("error")}
                continue
            entry = {
                "bbox": r["bbox"],
                "elapsed_s": r.get("elapsed_s"),
            }
            if legacy and legacy.get("ok") and engine != "legacy":
                entry["max_delta"] = _max_delta(legacy["positions"], r["positions"])
            scenario_summary[engine] = entry
        summary[scenario] = scenario_summary
    return summary


def _max_delta(a: dict, b: dict) -> int:
    common = set(a) & set(b)
    if not common:
        return 0
    return max(
        max(abs(a[k]["xpos"] - b[k]["xpos"]), abs(a[k]["ypos"] - b[k]["ypos"]))
        for k in common
    )


# ---------------------------------------------------------------------------
# Entry points: pytest test class + standalone main.
# ---------------------------------------------------------------------------
class CompareEnginesTest(unittest.TestCase):
    """Pytest entry point. Runs every scenario under every available engine
    and writes outputs. Does not assert correctness — that's for the visual
    review pass — but does fail loudly if any engine raises.
    """
    def test_compare(self):
        scenarios = discover_scenarios()
        if not scenarios:
            self.skipTest("No scenarios defined yet (skeleton harness)")

        results = []
        for scenario in scenarios:
            for engine in ENGINES:
                if not _engine_available(engine):
                    continue
                result = run_one(scenario, engine)
                results.append(result)

        # Per-scenario JSON
        for r in results:
            path = _OUTPUT_DIR / f"compare_{r['scenario']}_{r['engine']}.json"
            with open(path, "w") as fh:
                json.dump(r, fh, indent=2, default=str)

        # Summary CSV
        summary = diff_against_legacy(results)
        csv_path = _OUTPUT_DIR / "compare_summary.csv"
        with open(csv_path, "w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["scenario", "engine", "bbox", "elapsed_s", "max_delta_vs_legacy", "error"])
            for scenario, engines in summary.items():
                for engine, info in engines.items():
                    writer.writerow([
                        scenario, engine,
                        info.get("bbox"),
                        info.get("elapsed_s"),
                        info.get("max_delta", ""),
                        info.get("error", ""),
                    ])

        # Hard-fail if any engine errored on a scenario it claims to support.
        errors = [r for r in results if not r.get("ok")]
        self.assertFalse(errors, msg=f"Engine errors: {errors}")


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    only = None
    for arg in argv:
        if arg.startswith("--engines="):
            only = arg.split("=", 1)[1].split(",")

    scenarios = discover_scenarios()
    if not scenarios:
        print("No scenarios discovered (skeleton harness).")
        return 0

    engines = [e for e in ENGINES if (only is None or e in only) and _engine_available(e)]
    print(f"Engines: {engines}")
    print(f"Scenarios: {[s['name'] for s in scenarios]}")
    for scenario in scenarios:
        for engine in engines:
            r = run_one(scenario, engine)
            status = "OK" if r["ok"] else f"ERR ({r.get('error')})"
            print(f"  {scenario['name']:30s}  {engine:8s}  {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
