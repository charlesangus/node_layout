"""Integration tests for freeze-group layout behaviour.

These tests run the real layout engine inside headless Nuke (nuke -t) against
.nk fixture files, then use nuke_parser to read back positions and assert
correctness.  A PNG is also generated so you can visually inspect the result.

Each test targets a known bug from the Phase 16 UAT failure report:

  Scenario A (test_freeze_upstream_basic)
    Bug B — non-frozen nodes upstream of a freeze block are unreachable by
    place_subtree (path blocked by freeze_excluded_ids) and are never
    repositioned.  Source must end up directly above FrozenGrade1 after
    layout_upstream(Write1).

  Scenario B (test_freeze_selected_type_mismatch)
    Bug A — ``node_filter -= freeze_excluded_ids`` is a no-op in
    layout_selected (set[Node] - set[int]); non-root freeze members are
    freely repositioned, breaking block integrity.  Relative offsets inside
    each freeze block must be preserved after layout_selected.

  Scenario C (test_freeze_horizontal_override)
    Bug C — BFS for horizontal replay root does not skip frozen nodes, so a
    frozen node with mode=horizontal becomes the replay root.  After layout,
    FrozenHoriz must NOT have been used as the horizontal spine root.

Requires:
    nuke (at /home/latuser/.local/bin/nuke — standard install)
    nuke_parser (pip-installed from GitHub clone)
    ImageMagick ``convert`` command
"""

import json
import os
import subprocess
import sys
import unittest

# Make sure dag_viz is importable from this file's directory.
_TESTS_DIR = os.path.dirname(__file__)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

try:
    from dag_viz import render_dag  # noqa: E402
    _NUKE_PARSER_AVAILABLE = True
except ImportError:
    _NUKE_PARSER_AVAILABLE = False
    render_dag = None

_FIXTURES = os.path.join(os.path.dirname(__file__), "..", "nuke_tests", "fixtures")
_RUNNER = os.path.join(os.path.dirname(__file__), "..", "nuke_tests", "run_layout.py")
_NUKE = "/home/latuser/.local/bin/nuke"

# Where to write test output files (PNGs + JSONs).  Use the nuke_tests dir so
# they survive the test run and can be inspected.
_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "nuke_tests", "output")


def _ensure_output_dir():
    os.makedirs(_OUTPUT_DIR, exist_ok=True)


def _run_nuke_layout(fixture_name, command, root_node=None, select_nodes=None,
                     output_nk_name=None):
    """Run nuke -t with run_layout.py against a fixture.

    Returns the parsed positions dict on success, or raises AssertionError
    with Nuke's stdout/stderr if the process fails.
    """
    _ensure_output_dir()
    fixture_path = os.path.join(_FIXTURES, fixture_name)
    positions_path = os.path.join(_OUTPUT_DIR, fixture_name.replace(".nk", "_positions.json"))
    output_nk = None
    if output_nk_name:
        output_nk = os.path.join(_OUTPUT_DIR, output_nk_name)

    env = os.environ.copy()
    env["NL_INPUT"] = fixture_path
    env["NL_POSITIONS_JSON"] = positions_path
    env["NL_COMMAND"] = command
    if root_node:
        env["NL_ROOT_NODE"] = root_node
    if select_nodes:
        env["NL_SELECT"] = ",".join(select_nodes)
    if output_nk:
        env["NL_OUTPUT"] = output_nk

    result = subprocess.run(
        [_NUKE, "-t", _RUNNER],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    stdout = result.stdout + result.stderr
    if result.returncode != 0:
        raise AssertionError(
            f"nuke -t returned {result.returncode}:\n{stdout}"
        )

    with open(positions_path) as fh:
        positions = json.load(fh)

    return positions, output_nk or fixture_path


def _generate_png(nk_path, png_name, title=None):
    """Render *nk_path* to a PNG in the output directory."""
    _ensure_output_dir()
    png_path = os.path.join(_OUTPUT_DIR, png_name)
    render_dag(nk_path, png_path, title=title)
    return png_path


@unittest.skipIf(not _NUKE_PARSER_AVAILABLE, "nuke_parser required for integration tests")
class TestFreezeUpstreamBasic(unittest.TestCase):
    """Scenario A: non-frozen upstream node must be repositioned above the freeze block."""

    @classmethod
    def setUpClass(cls):
        cls.positions, cls.output_nk = _run_nuke_layout(
            "freeze_upstream_basic.nk",
            command="layout_upstream",
            root_node="Write1",
            output_nk_name="freeze_upstream_basic_after.nk",
        )

        # Generate before/after PNGs.
        fixture_path = os.path.join(_FIXTURES, "freeze_upstream_basic.nk")
        cls.before_png = _generate_png(
            fixture_path, "freeze_upstream_basic_BEFORE.png", title="BEFORE layout"
        )
        cls.after_png = _generate_png(
            cls.output_nk, "freeze_upstream_basic_AFTER.png", title="AFTER layout"
        )

    def test_source_repositioned_above_frozen_grade1(self):
        """Source (non-frozen) must end up above FrozenGrade1 in Y (lower ypos)."""
        source_y = self.positions["Source"]["ypos"]
        frozen1_y = self.positions["FrozenGrade1"]["ypos"]
        self.assertLess(
            source_y,
            frozen1_y,
            f"Source (ypos={source_y}) should be above FrozenGrade1 (ypos={frozen1_y}), "
            f"but it wasn't repositioned. Bug B still present.",
        )

    def test_freeze_block_relative_offset_preserved(self):
        """FrozenGrade1 must maintain its relative Y offset from FrozenGrade2."""
        initial_delta = -200 - (-100)  # from fixture: FrozenGrade1.ypos - FrozenGrade2.ypos
        grade1_y = self.positions["FrozenGrade1"]["ypos"]
        grade2_y = self.positions["FrozenGrade2"]["ypos"]
        actual_delta = grade1_y - grade2_y
        snap_tolerance = 16  # 2× snap threshold
        self.assertAlmostEqual(
            actual_delta,
            initial_delta,
            delta=snap_tolerance,
            msg=(
                f"Freeze block relative offset broken: "
                f"FrozenGrade1.y={grade1_y}, FrozenGrade2.y={grade2_y}, "
                f"delta={actual_delta} (expected ~{initial_delta})"
            ),
        )

    def test_write_is_below_freeze_root(self):
        """Write1 must be downstream (higher Y) of FrozenGrade2."""
        write_y = self.positions["Write1"]["ypos"]
        grade2_y = self.positions["FrozenGrade2"]["ypos"]
        self.assertGreater(write_y, grade2_y)

    def test_pngs_generated(self):
        """Smoke test: before/after PNGs must exist on disk."""
        self.assertTrue(os.path.exists(self.before_png), f"Missing: {self.before_png}")
        self.assertTrue(os.path.exists(self.after_png), f"Missing: {self.after_png}")


@unittest.skipIf(not _NUKE_PARSER_AVAILABLE, "nuke_parser required for integration tests")
class TestFreezeSelectedTypeMismatch(unittest.TestCase):
    """Scenario B: freeze block relative offsets must survive layout_selected."""

    @classmethod
    def setUpClass(cls):
        cls.positions, cls.output_nk = _run_nuke_layout(
            "freeze_selected_type_mismatch.nk",
            command="layout_selected",
            output_nk_name="freeze_selected_type_mismatch_after.nk",
        )
        fixture_path = os.path.join(_FIXTURES, "freeze_selected_type_mismatch.nk")
        cls.before_png = _generate_png(
            fixture_path, "freeze_selected_type_mismatch_BEFORE.png", title="BEFORE layout"
        )
        cls.after_png = _generate_png(
            cls.output_nk, "freeze_selected_type_mismatch_AFTER.png", title="AFTER layout"
        )

    def test_left_freeze_block_relative_offset_preserved(self):
        """LeftSource/LeftRoot relative Y offset must be maintained after layout_selected."""
        initial_delta = -300 - (-200)  # LeftSource.ypos - LeftRoot.ypos
        left_source_y = self.positions["LeftSource"]["ypos"]
        left_root_y = self.positions["LeftRoot"]["ypos"]
        actual_delta = left_source_y - left_root_y
        snap_tolerance = 16
        self.assertAlmostEqual(
            actual_delta,
            initial_delta,
            delta=snap_tolerance,
            msg=(
                f"Left freeze block relative offset broken: "
                f"LeftSource.y={left_source_y}, LeftRoot.y={left_root_y}, "
                f"delta={actual_delta} (expected ~{initial_delta}). "
                f"Bug A (type mismatch) still present."
            ),
        )

    def test_right_freeze_block_relative_offset_preserved(self):
        """RightSource/RightRoot relative Y offset must be maintained after layout_selected."""
        initial_delta = -300 - (-200)
        right_source_y = self.positions["RightSource"]["ypos"]
        right_root_y = self.positions["RightRoot"]["ypos"]
        actual_delta = right_source_y - right_root_y
        snap_tolerance = 16
        self.assertAlmostEqual(
            actual_delta,
            initial_delta,
            delta=snap_tolerance,
            msg=(
                f"Right freeze block relative offset broken: "
                f"RightSource.y={right_source_y}, RightRoot.y={right_root_y}, "
                f"delta={actual_delta} (expected ~{initial_delta}). "
                f"Bug A (type mismatch) still present."
            ),
        )

    def test_pngs_generated(self):
        self.assertTrue(os.path.exists(self.before_png))
        self.assertTrue(os.path.exists(self.after_png))


@unittest.skipIf(not _NUKE_PARSER_AVAILABLE, "nuke_parser required for integration tests")
class TestFreezeHorizontalOverride(unittest.TestCase):
    """Scenario C: frozen nodes with mode=horizontal must not become replay roots."""

    @classmethod
    def setUpClass(cls):
        cls.positions, cls.output_nk = _run_nuke_layout(
            "freeze_horizontal_override.nk",
            command="layout_upstream",
            root_node="Write1",
            output_nk_name="freeze_horizontal_override_after.nk",
        )
        fixture_path = os.path.join(_FIXTURES, "freeze_horizontal_override.nk")
        cls.before_png = _generate_png(
            fixture_path, "freeze_horizontal_override_BEFORE.png", title="BEFORE layout"
        )
        cls.after_png = _generate_png(
            cls.output_nk, "freeze_horizontal_override_AFTER.png", title="AFTER layout"
        )

    def test_frozen_horiz_is_not_horizontal_root(self):
        """FrozenHoriz must not be placed as if it were the horizontal spine root.

        When FrozenHoriz (frozen, mode=horizontal) is incorrectly selected as
        the horizontal replay root, the layout places it at the right end of a
        horizontal spine and Merge1 is placed to its right — meaning
        FrozenHoriz.xpos < Merge1.xpos.  With the correct fix, no horizontal
        spine walk should start at a frozen node, so the layout falls back to
        vertical and FrozenHoriz should remain above (lower Y than) Merge1.
        """
        frozen_horiz_y = self.positions["FrozenHoriz"]["ypos"]
        merge1_y = self.positions["Merge1"]["ypos"]
        self.assertLess(
            frozen_horiz_y,
            merge1_y,
            f"FrozenHoriz (ypos={frozen_horiz_y}) should be above Merge1 (ypos={merge1_y}). "
            f"If FrozenHoriz was used as horizontal root, it ends up at the same Y as Merge1. "
            f"Bug C still present.",
        )

    def test_pngs_generated(self):
        self.assertTrue(os.path.exists(self.before_png))
        self.assertTrue(os.path.exists(self.after_png))


@unittest.skipIf(not _NUKE_PARSER_AVAILABLE, "nuke_parser required for integration tests")
class TestFreezeHorizontalBboxOverlap(unittest.TestCase):
    """Scenario D: frozen subtree bbox must not overlap adjacent subtree bboxes
    after layout_selected_horizontal on spine Merge nodes.

    The fixture has four vertical chains (CheckerBoard→Grade→Blur→Transform)
    feeding three Merge nodes in a chain.  The second chain's Grade2/Blur2/Transform2
    are in a freeze group with widely scattered original positions.

    After layout_selected_horizontal on the Merge spine, each subtree above a
    spine node must occupy its own horizontal band with no overlap.
    """

    # Standard node width in Nuke
    NODE_WIDTH = 80

    @classmethod
    def setUpClass(cls):
        cls.positions, cls.output_nk = _run_nuke_layout(
            "frozen_horizontal.nk",
            command="layout_selected_horizontal",
            select_nodes=["Merge1", "Merge2", "Merge3"],
            output_nk_name="frozen_horizontal_horiz_after.nk",
        )
        fixture_path = os.path.join(_FIXTURES, "frozen_horizontal.nk")
        cls.before_png = _generate_png(
            fixture_path, "frozen_horizontal_BEFORE.png", title="BEFORE layout"
        )
        cls.after_png = _generate_png(
            cls.output_nk, "frozen_horizontal_AFTER.png", title="AFTER layout"
        )

    def _subtree_bbox(self, node_names):
        """Return (min_x, max_x_right_edge, min_y, max_y_bottom_edge) for named nodes."""
        min_x = min(self.positions[name]["xpos"] for name in node_names)
        max_x = max(self.positions[name]["xpos"] + self.NODE_WIDTH for name in node_names)
        min_y = min(self.positions[name]["ypos"] for name in node_names)
        max_y = max(self.positions[name]["ypos"] + 28 for name in node_names)
        return min_x, max_x, min_y, max_y

    def test_frozen_subtree_does_not_overlap_left_subtree(self):
        """The freeze block (Grade2/Blur2/Transform2) plus CheckerBoard2 must not
        overlap horizontally with the Transform1 column (input[0] subtree)."""
        frozen_subtree = ["Transform2", "Blur2", "Grade2", "CheckerBoard2"]
        left_subtree = ["Transform1", "Blur1", "Grade1", "CheckerBoard1"]

        frozen_min_x, frozen_max_x, _, _ = self._subtree_bbox(frozen_subtree)
        left_min_x, left_max_x, _, _ = self._subtree_bbox(left_subtree)

        # Left subtree's right edge must be to the left of frozen subtree's left edge
        self.assertLessEqual(
            left_max_x,
            frozen_min_x,
            f"Left subtree right edge ({left_max_x}) overlaps frozen subtree "
            f"left edge ({frozen_min_x}). Freeze block bbox not accounted for "
            f"in horizontal spacing.",
        )

    def test_frozen_subtree_does_not_overlap_right_subtree(self):
        """The freeze block must not overlap with the Transform3 column (Merge2's
        side input subtree)."""
        frozen_subtree = ["Transform2", "Blur2", "Grade2", "CheckerBoard2"]
        right_subtree = ["Transform3", "Blur3", "Grade3", "CheckerBoard3"]

        frozen_min_x, frozen_max_x, _, _ = self._subtree_bbox(frozen_subtree)
        right_min_x, right_max_x, _, _ = self._subtree_bbox(right_subtree)

        self.assertLessEqual(
            frozen_max_x,
            right_min_x,
            f"Frozen subtree right edge ({frozen_max_x}) overlaps right subtree "
            f"left edge ({right_min_x}). Freeze block bbox not accounted for "
            f"in horizontal spacing.",
        )

    def test_freeze_block_relative_offsets_preserved(self):
        """Frozen members must maintain their root-relative offsets after layout."""
        # Original offsets from Transform2 (root): Blur2=(-288,-98), Grade2=(49,-107)
        transform2_x = self.positions["Transform2"]["xpos"]
        transform2_y = self.positions["Transform2"]["ypos"]

        blur2_x = self.positions["Blur2"]["xpos"]
        blur2_y = self.positions["Blur2"]["ypos"]
        blur2_offset_x = blur2_x - transform2_x
        blur2_offset_y = blur2_y - transform2_y

        grade2_x = self.positions["Grade2"]["xpos"]
        grade2_y = self.positions["Grade2"]["ypos"]
        grade2_offset_x = grade2_x - transform2_x
        grade2_offset_y = grade2_y - transform2_y

        # Original offsets: Blur2 was at (248,-40), Transform2 at (536,58)
        # Blur2 offset = (248-536, -40-58) = (-288, -98)
        self.assertAlmostEqual(blur2_offset_x, -288, delta=2,
                               msg=f"Blur2 x-offset from root: {blur2_offset_x} (expected -288)")
        self.assertAlmostEqual(blur2_offset_y, -98, delta=2,
                               msg=f"Blur2 y-offset from root: {blur2_offset_y} (expected -98)")

        # Grade2 offset = (585-536, -49-58) = (49, -107)
        self.assertAlmostEqual(grade2_offset_x, 49, delta=2,
                               msg=f"Grade2 x-offset from root: {grade2_offset_x} (expected 49)")
        self.assertAlmostEqual(grade2_offset_y, -107, delta=2,
                               msg=f"Grade2 y-offset from root: {grade2_offset_y} (expected -107)")

    def test_external_input_follows_connecting_member(self):
        """CheckerBoard2 (non-frozen) must be positioned above Grade2 (frozen),
        not stranded at the pre-restore position."""
        checkerboard2_x = self.positions["CheckerBoard2"]["xpos"]
        grade2_x = self.positions["Grade2"]["xpos"]
        # CheckerBoard2 should be centered above Grade2 (same x, lower y)
        self.assertAlmostEqual(
            checkerboard2_x, grade2_x, delta=2,
            msg=(
                f"CheckerBoard2 x={checkerboard2_x} should be aligned with "
                f"Grade2 x={grade2_x} (external input must follow freeze restore)"
            ),
        )
        checkerboard2_y = self.positions["CheckerBoard2"]["ypos"]
        grade2_y = self.positions["Grade2"]["ypos"]
        self.assertLess(
            checkerboard2_y, grade2_y,
            f"CheckerBoard2 (y={checkerboard2_y}) must be above Grade2 (y={grade2_y})",
        )

    def test_pngs_generated(self):
        self.assertTrue(os.path.exists(self.before_png))
        self.assertTrue(os.path.exists(self.after_png))


if __name__ == "__main__":
    unittest.main(verbosity=2)
