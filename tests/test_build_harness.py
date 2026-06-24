"""Authoritative pytest for the v1.5 documentation pipeline build harness.

Shells out to `make <target>` via subprocess and asserts that each stage:
  - exits 0
  - prints the expected ==> [<stage>] (placeholder) banner
  - produces the expected stub artifact on disk

Also asserts the full ordered chain (scenes -> capture -> docs -> pdf) and
that `make help` lists every stage.

No Nuke dependency — runs safely on the existing ubuntu-24.04 CI runner.
"""

import os
import subprocess
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
_DOCS_DIR = os.path.join(_REPO_ROOT, "docs")


def _run_make(target, force_rebuild=False):
    """Run a make target from the repo root and return the CompletedProcess."""
    cmd = ["make"]
    if force_rebuild:
        cmd.append("-B")
    cmd.append(target)
    return subprocess.run(
        cmd,
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestScenesStage(unittest.TestCase):
    def test_scenes_exits_zero_with_banner_and_stub(self):
        result = _run_make("scenes", force_rebuild=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("==> [scenes] (placeholder)", result.stdout)
        stub_path = os.path.join(_DOCS_DIR, "scenes", "demo.nk.stub")
        self.assertTrue(os.path.isfile(stub_path), f"stub artifact missing: {stub_path}")


class TestCaptureStage(unittest.TestCase):
    def test_capture_exits_zero_with_banner_and_stub(self):
        result = _run_make("capture", force_rebuild=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("==> [capture] (placeholder)", result.stdout)
        stub_path = os.path.join(_DOCS_DIR, "images", "capture.stub")
        self.assertTrue(os.path.isfile(stub_path), f"stub artifact missing: {stub_path}")


class TestDocsStage(unittest.TestCase):
    def test_docs_exits_zero_with_banner_and_stub(self):
        result = _run_make("docs", force_rebuild=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("==> [docs] (placeholder)", result.stdout)
        stub_path = os.path.join(_DOCS_DIR, "manual.md.stub")
        self.assertTrue(os.path.isfile(stub_path), f"stub artifact missing: {stub_path}")


class TestPdfStage(unittest.TestCase):
    def test_pdf_exits_zero_with_banner_and_stub(self):
        result = _run_make("pdf", force_rebuild=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("==> [pdf] (placeholder)", result.stdout)
        stub_path = os.path.join(_DOCS_DIR, "manual.pdf")
        self.assertTrue(os.path.isfile(stub_path), f"stub artifact missing: {stub_path}")


class TestHelpTarget(unittest.TestCase):
    def test_help_lists_all_stages_and_test(self):
        result = _run_make("help")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for stage in ("scenes", "capture", "docs", "pdf", "test"):
            self.assertIn(stage, result.stdout, f"'make help' did not mention stage: {stage}")


class TestFullChain(unittest.TestCase):
    def test_all_runs_stages_in_order(self):
        result = _run_make("all", force_rebuild=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        banners = [
            "==> [scenes] (placeholder)",
            "==> [capture] (placeholder)",
            "==> [docs] (placeholder)",
            "==> [pdf] (placeholder)",
        ]
        for banner in banners:
            self.assertIn(banner, result.stdout, f"banner missing from output: {banner}")

        # Assert scenes appears before capture appears before docs appears before pdf
        scenes_index = result.stdout.index("==> [scenes] (placeholder)")
        capture_index = result.stdout.index("==> [capture] (placeholder)")
        docs_index = result.stdout.index("==> [docs] (placeholder)")
        pdf_index = result.stdout.index("==> [pdf] (placeholder)")
        self.assertLess(scenes_index, capture_index, "scenes must precede capture")
        self.assertLess(capture_index, docs_index, "capture must precede docs")
        self.assertLess(docs_index, pdf_index, "docs must precede pdf")


if __name__ == "__main__":
    unittest.main()
