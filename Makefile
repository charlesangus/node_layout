# node_layout v1.5 Documentation Pipeline Build Harness
# Stages: scenes -> capture -> docs -> pdf
# Each stage is a file target whose name is the stub artifact it produces.
# Later phases (23-26) replace placeholder recipes without re-wiring targets,
# dependencies, or output paths.

.DEFAULT_GOAL := all

.PHONY: all scenes capture docs pdf test clean help

# ---------------------------------------------------------------------------
# File targets (dependency chain: scenes -> capture -> docs -> pdf)
# ---------------------------------------------------------------------------

docs/scenes/demo.nk.stub:
	@mkdir -p docs/scenes
	@echo "==> [scenes] (placeholder)"
	@echo "scenes-placeholder" > docs/scenes/demo.nk.stub

docs/images/capture.stub: docs/scenes/demo.nk.stub
	@mkdir -p docs/images
	@echo "==> [capture] (placeholder)"
	@echo "capture-placeholder" > docs/images/capture.stub

docs/manual.md.stub: docs/images/capture.stub
	@mkdir -p docs
	@echo "==> [docs] (placeholder)"
	@echo "docs-placeholder" > docs/manual.md.stub

docs/manual.pdf: docs/manual.md.stub
	@mkdir -p docs
	@echo "==> [pdf] (placeholder)"
	@echo "pdf-placeholder" > docs/manual.pdf

# ---------------------------------------------------------------------------
# PHONY convenience aliases (runnable by bare stage name)
# ---------------------------------------------------------------------------

scenes: docs/scenes/demo.nk.stub

capture: docs/images/capture.stub

docs: docs/manual.md.stub

pdf: docs/manual.pdf

# ---------------------------------------------------------------------------
# PHONY utility targets
# ---------------------------------------------------------------------------

all: pdf

test:
	pytest tests/test_build_harness.py -v

clean:
	rm -f docs/scenes/demo.nk.stub docs/images/capture.stub docs/manual.md.stub docs/manual.pdf
	@echo "==> [clean] removed stub artifacts and docs/manual.pdf"

help:
	@echo "node_layout v1.5 Documentation Pipeline"
	@echo ""
	@echo "Targets:"
	@echo "  all      Run the full pipeline: scenes -> capture -> docs -> pdf (default)"
	@echo "  scenes   Generate demo .nk scene files (docs/scenes/demo.nk.stub)"
	@echo "  capture  Capture DAG screenshots as PNGs (docs/images/capture.stub)"
	@echo "  docs     Assemble markdown documentation (docs/manual.md.stub)"
	@echo "  pdf      Build PDF from markdown (docs/manual.pdf)"
	@echo "  test     Run the build harness pytest suite"
	@echo "  clean    Remove generated stub artifacts and docs/manual.pdf"
	@echo "  help     Show this help message"
