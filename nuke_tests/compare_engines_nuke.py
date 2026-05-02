"""Headless-Nuke harness: run fixtures through supported layout engines and
emit position diffs + visual snapshots.

Usage::

    python3 nuke_tests/compare_engines_nuke.py
        # spawns `nuke -t run_layout.py` once per (fixture, supported engine)
        # writes nuke_tests/output/compare_<fixture>_<engine>.json
        # writes nuke_tests/output/compare_<fixture>_<engine>.png  (via dag_viz)
        # writes nuke_tests/output/compare_summary.json

Each fixture in ``nuke_tests/fixtures/`` is run against every engine name
supported by the current checkout. The bbox-only branch intentionally reports
only ``bbox`` so deleted legacy/shape engines cannot produce misleading
same-engine comparisons.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
from typing import Any

_HERE = pathlib.Path(__file__).resolve().parent
_WORKSPACE = _HERE.parent
if str(_WORKSPACE) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE))

import node_layout_engine  # noqa: E402

_FIXTURES_DIR = _HERE / "fixtures"
_OUTPUT_DIR = _HERE / "output"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
_RUN_LAYOUT = _HERE / "run_layout.py"


ENGINES = node_layout_engine.list_registered_engines()


# Per-fixture run config. Pulled out as a table so subagents can extend
# without touching loop logic. Each entry says: fixture file, command
# to run, and any extra env. NL_ROOT_NODE / NL_SELECT vary per fixture
# because each fixture's "root" node has a different name.
FIXTURES: list[dict[str, Any]] = [
    # {"fixture": "frozen_horizontal.nk", "command": "layout_selected_horizontal", "select": "..."},
    # {"fixture": "frozen_vertical.nk",   "command": "layout_upstream",            "root": "..."},
    # ...
    # Subagents fill these in based on each fixture's actual node names.
    # Until then, the harness will iterate fixtures discovered on disk and
    # default to layout_upstream on the most-downstream Write node.
]


def _nuke_binary() -> str | None:
    """Find a Nuke binary. Honors NUKE_BIN env, then a few standard paths."""
    env = os.environ.get("NUKE_BIN")
    if env and pathlib.Path(env).exists():
        return env
    for candidate in ("nuke", "Nuke16.0", "Nuke15.1", "Nuke14.0"):
        path = shutil.which(candidate)
        if path:
            return path
    for fallback in (
        "/home/latuser/.local/bin/nuke",
        "/usr/local/Nuke16.0v6/Nuke16.0",
    ):
        if pathlib.Path(fallback).exists():
            return fallback
    return None


def _run_fixture(
    fixture_path: pathlib.Path,
    engine: str,
    entry: dict[str, Any],
    nuke_bin: str,
) -> dict[str, Any]:
    """Spawn `nuke -t run_layout.py` with NL_* env vars set for this run."""
    out_json = _OUTPUT_DIR / f"compare_{fixture_path.stem}_{engine}.json"
    out_nk = _OUTPUT_DIR / f"compare_{fixture_path.stem}_{engine}.nk"
    env = dict(os.environ)
    env["NL_INPUT"] = str(fixture_path)
    env["NL_POSITIONS_JSON"] = str(out_json)
    env["NL_OUTPUT"] = str(out_nk)
    env["NL_ENGINE"] = engine
    env["NL_COMMAND"] = entry.get("command", "layout_upstream")
    if "root" in entry:
        env["NL_ROOT_NODE"] = entry["root"]
    if "select" in entry:
        env["NL_SELECT"] = entry["select"]

    try:
        proc = subprocess.run(
            [nuke_bin, "-t", str(_RUN_LAYOUT)],
            env=env, timeout=60, capture_output=True, text=True,
        )
        if proc.returncode != 0:
            return {
                "fixture": fixture_path.name,
                "engine": engine,
                "ok": False,
                "error": f"exit {proc.returncode}",
                "stdout": proc.stdout[-2000:],
                "stderr": proc.stderr[-2000:],
            }
        with open(out_json) as fh:
            positions = json.load(fh)
        return {
            "fixture": fixture_path.name,
            "engine": engine,
            "ok": True,
            "positions": positions,
            "out_json": str(out_json),
            "out_nk": str(out_nk),
        }
    except subprocess.TimeoutExpired:
        return {"fixture": fixture_path.name, "engine": engine, "ok": False, "error": "timeout"}
    except Exception as e:  # noqa: BLE001
        return {"fixture": fixture_path.name, "engine": engine, "ok": False, "error": str(e)}


def _diff(legacy_positions: dict, other_positions: dict) -> dict:
    """Compute per-node Δx/Δy and overall max-Δ between two engines."""
    common = set(legacy_positions) & set(other_positions)
    deltas = {
        name: {
            "dx": other_positions[name]["xpos"] - legacy_positions[name]["xpos"],
            "dy": other_positions[name]["ypos"] - legacy_positions[name]["ypos"],
        }
        for name in common
    }
    max_d = max(
        (max(abs(d["dx"]), abs(d["dy"])) for d in deltas.values()),
        default=0,
    )
    only_in_legacy = sorted(set(legacy_positions) - common)
    only_in_other = sorted(set(other_positions) - common)
    return {
        "deltas": deltas,
        "max_delta": max_d,
        "only_in_legacy": only_in_legacy,
        "only_in_other": only_in_other,
    }


def main() -> int:
    nuke_bin = _nuke_binary()
    if nuke_bin is None:
        print("error: no Nuke binary found. Set NUKE_BIN to point at your Nuke executable.")
        return 2

    print(f"Using nuke: {nuke_bin}")

    # Build the per-fixture entry table from the inventory. If FIXTURES
    # was filled in (subagent), use that. Otherwise auto-discover .nk
    # files and default to layout_upstream on selectAll-equivalent.
    entries = list(FIXTURES)
    if not entries:
        for f in sorted(_FIXTURES_DIR.glob("*.nk")):
            entries.append({"fixture": f.name, "command": "layout_selected"})

    results: list[dict] = []
    for entry in entries:
        fixture = _FIXTURES_DIR / entry["fixture"]
        if not fixture.exists():
            print(f"  skip {entry['fixture']} (missing)")
            continue
        for engine in ENGINES:
            print(f"  {entry['fixture']:35s}  {engine:8s} ", end="", flush=True)
            r = _run_fixture(fixture, engine, entry, nuke_bin)
            print("OK" if r["ok"] else f"ERR ({r.get('error')})")
            results.append(r)

    # Pair up a baseline engine vs each other supported engine per fixture.
    by_fixture: dict[str, dict[str, dict]] = {}
    for r in results:
        by_fixture.setdefault(r["fixture"], {})[r["engine"]] = r

    summary: dict[str, Any] = {}
    for fixture, per_engine in by_fixture.items():
        baseline_name = "legacy" if "legacy" in per_engine else ENGINES[0]
        baseline = per_engine.get(baseline_name)
        if not (baseline and baseline.get("ok")):
            summary[fixture] = {"baseline": baseline_name, "baseline_ok": False}
            continue
        entry: dict[str, Any] = {
            "baseline": baseline_name,
            "baseline_ok": True,
        }
        for engine, r in per_engine.items():
            if engine == baseline_name or not r.get("ok"):
                continue
            entry[engine] = _diff(baseline["positions"], r["positions"])
        summary[fixture] = entry

    summary_path = _OUTPUT_DIR / "compare_summary.json"
    with open(summary_path, "w") as fh:
        json.dump(summary, fh, indent=2)
    print(f"\nSummary: {summary_path}")

    # Hard-fail if any engine errored.
    errors = [r for r in results if not r.get("ok")]
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
