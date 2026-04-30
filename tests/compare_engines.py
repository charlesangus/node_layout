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
    try:
        # Trigger registration. The bbox/shape modules only exist on their
        # respective branches.
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
    """Return scenario dicts. Skeleton: empty list (subagents fill in).

    Each scenario looks like::

        {
            "name": "vertical_3input",
            "build": _build_vertical_3input,   # callable returning (root, selection)
            "command": "layout_upstream",      # or layout_selected / layout_selected_horizontal
            "scheme_multiplier": None,
        }
    """
    return []


# ---------------------------------------------------------------------------
# Per-engine runner. Sets NODE_LAYOUT_ENGINE, builds scenario, runs,
# captures positions.
# ---------------------------------------------------------------------------
def run_one(scenario: dict[str, Any], engine: str) -> dict[str, Any]:
    """Run one scenario under one engine and return a result dict."""
    os.environ["NODE_LAYOUT_ENGINE"] = engine
    try:
        root, selection = scenario["build"]()

        import node_layout
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

        positions = _collect_positions(root, selection)
        bbox = _bbox_of(positions)
        return {
            "engine": engine,
            "scenario": scenario["name"],
            "positions": positions,
            "bbox": bbox,
            "elapsed_s": elapsed,
            "ok": True,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "engine": engine,
            "scenario": scenario["name"],
            "error": f"{type(e).__name__}: {e}",
            "ok": False,
        }
    finally:
        os.environ.pop("NODE_LAYOUT_ENGINE", None)


def _collect_positions(root, selection) -> dict[str, dict]:
    """Record xpos/ypos for every node in the scenario's universe.

    Subagents implementing the harness fully will walk root + selection
    + their upstream closure. Skeleton returns empty.
    """
    return {}


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
