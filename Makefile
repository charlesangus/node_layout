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

.PHONY: all pdf clean

all: pdf

pdf: $(USER_GUIDE_PDF)

$(USER_GUIDE_PDF): $(USER_GUIDE_MD) $(PANDOC_DEFAULTS) $(PANDOC_LUA_FILTER) $(LATEX_RESOURCE_DIR)/trainingDoc.cls $(LATEX_RESOURCE_DIR)/logo.pdf
	TEXINPUTS=./$(LATEX_RESOURCE_DIR): $(PANDOC) $(USER_GUIDE_MD) \
		--defaults $(PANDOC_DEFAULTS) \
		--lua-filter $(PANDOC_LUA_FILTER) \
		-o $(USER_GUIDE_PDF)

# A `screenshots` target for regenerating documentation screenshots from a
# running Nuke instance will be added by a later milestone. It must remain
# independent of `pdf` (the pdf target must never trigger a Nuke run).

clean:
	rm -f $(USER_GUIDE_PDF)
	rm -f docs/*.aux docs/*.log docs/*.out
	rm -rf build/
