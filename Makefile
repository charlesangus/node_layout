# Makefile for building Node Layout project documentation.
#
# `make pdf` renders docs/user-guide.md into docs/user-guide.pdf using
# pandoc, the pdf.yaml defaults file, and the float-images lua filter.
# The LaTeX engine (xelatex, per docs/pandoc/pdf.yaml) needs to find the
# custom trainingDoc.cls document class and the logo.pdf image, both of
# which live under docs/latex. TEXINPUTS is set to a path relative to the
# repository root (where make is expected to run from) so this works on
# any machine without hardcoding a local absolute path.

PANDOC ?= pandoc

USER_GUIDE_MD := docs/user-guide.md
USER_GUIDE_PDF := docs/user-guide.pdf
PANDOC_DEFAULTS := docs/pandoc/pdf.yaml
PANDOC_LUA_FILTER := docs/pandoc/float-images.lua
LATEX_RESOURCE_DIR := docs/latex

# Settings for `make screenshotter-setup`, which installs the
# `nuke-docs-screenshotter` tool (console command `nuke_dag_capture_auto`)
# used by a later `screenshots` target to render documentation PNGs from
# Nuke. The tool is a separate GPL-licensed project and is cloned into a
# gitignored directory rather than vendored into this repository. All of
# these are overridable, e.g. `make screenshotter-setup NUKE=/path/to/nuke`.
SCREENSHOTTER_REPO ?= https://github.com/charlesangus/nuke-screenshotter.git
SCREENSHOTTER_DIR ?= .tools/nuke-screenshotter
NUKE ?= nuke
PIP ?= pip3
# --break-system-packages is needed on Debian/Ubuntu's "externally managed"
# system Python (PEP 668) to allow a --user install outside apt/pipx.
# Override if your pip does not need/support this flag.
PIP_INSTALL_ARGS ?= --user --break-system-packages

.PHONY: all pdf clean screenshotter-setup

all: pdf

pdf: $(USER_GUIDE_PDF)

$(USER_GUIDE_PDF): $(USER_GUIDE_MD) $(PANDOC_DEFAULTS) $(PANDOC_LUA_FILTER) $(LATEX_RESOURCE_DIR)/trainingDoc.cls $(LATEX_RESOURCE_DIR)/logo.pdf
	TEXINPUTS=./$(LATEX_RESOURCE_DIR): $(PANDOC) $(USER_GUIDE_MD) \
		--defaults $(PANDOC_DEFAULTS) \
		--lua-filter $(PANDOC_LUA_FILTER) \
		-o $(USER_GUIDE_PDF)

# Clones nuke-screenshotter (see SCREENSHOTTER_REPO/SCREENSHOTTER_DIR above)
# and installs it, exposing the `nuke_dag_capture_auto` console command.
# Safe to re-run: pulls latest if the clone already exists, then reinstalls.
# See docs/README-build.md for prerequisites (Nuke license, xvfb, Mesa
# software-GL) and how the tool is invoked.
screenshotter-setup:
	@if [ -d "$(SCREENSHOTTER_DIR)/.git" ]; then \
		git -C "$(SCREENSHOTTER_DIR)" pull; \
	else \
		mkdir -p "$$(dirname "$(SCREENSHOTTER_DIR)")"; \
		git clone "$(SCREENSHOTTER_REPO)" "$(SCREENSHOTTER_DIR)"; \
	fi
	$(PIP) install $(PIP_INSTALL_ARGS) "$(SCREENSHOTTER_DIR)"

# A `screenshots` target for regenerating documentation screenshots from a
# running Nuke instance will be added by a later milestone. It must remain
# independent of `pdf` (the pdf target must never trigger a Nuke run).

clean:
	rm -f $(USER_GUIDE_PDF)
	rm -f docs/*.aux docs/*.log docs/*.out
	rm -rf build/
