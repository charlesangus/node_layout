# Requirements — v1.5 Automated Documentation

**Milestone goal:** A local, single-command pipeline that programmatically generates demo DAG scenes from node_layout, captures them via `nuke-docs-screenshotter`, and assembles a hierarchical tutorial + reference manual covering all functionality — output as markdown (committed PNGs) and PDF (pandoc/LaTeX build artifact).

**Automation boundary:** Local-only. Screenshot capture requires an interactive Nuke GUI license, so nothing doc-related runs in GitHub Actions CI (consistent with the existing "no headless Nuke in CI" decision). The markdown→PDF stage needs only pandoc + LaTeX and can run anywhere, but is invoked locally as part of the same build command.

**Sequencing principle:** The build harness (Makefile) is scaffolded up front and each subsequent phase wires its stage into it, so every stage is testable as it lands rather than integrated all at once.

---

## v1.5 Requirements

### Build Pipeline (BUILD)
- [ ] **BUILD-01**: A single local command (Makefile) runs the full chain — generate scenes → capture screenshots → assemble markdown → build PDF. The Makefile is scaffolded first (skeleton with stage targets) and extended incrementally as each stage is implemented.
- [ ] **BUILD-02**: The build command and its prerequisites (Nuke, `nuke-docs-screenshotter`, pandoc, LaTeX) are documented.
- [ ] **BUILD-03**: Stages can run independently — e.g. rebuild the PDF from committed PNGs without re-capturing — for the no-Nuke case.

### Demo Scene Generation (SCENE)
- [ ] **SCENE-01**: A node_layout routine programmatically builds a demo `.nk` script containing one `screenshot:`-labelled backdrop per documented feature.
- [ ] **SCENE-02**: Each backdrop's slug maps deterministically to a feature so captured PNG filenames are stable across regenerations.
- [ ] **SCENE-03**: Generated scenes cover all functionality — vertical / horizontal / selected layout, multi-input fan alignment, mask placement, shrink/expand axis modes, freeze/unfreeze, every leader-key command, and prefs schemes.
- [ ] **SCENE-04**: Where a command transforms a DAG, the scene presents before/after states so the screenshot illustrates the effect.

### Screenshot Capture (CAP)
- [ ] **CAP-01**: A documented setup step installs `nuke-docs-screenshotter` (the `nuke_dag_capture_auto` CLI) as a build-time dependency.
- [ ] **CAP-02**: The pipeline invokes `nuke_dag_capture_auto` on the generated demo `.nk` to produce one PNG per backdrop into a docs image directory.
- [ ] **CAP-03**: Captured PNGs are committed to the repo so docs and PDF rebuild without a Nuke license.

### Documentation Content (DOC)
- [ ] **DOC-01**: A top-level overview introduces node_layout's main functions hierarchically.
- [ ] **DOC-02**: A tutorial/walkthrough guides a new user through common workflows (install, first layout, leader key, prefs).
- [ ] **DOC-03**: A reference section documents every menu command with a description and screenshot.
- [ ] **DOC-04**: The reference documents every leader-key binding (Shift+E entry plus V/Z/F/C/W/A/S/D/Q/E).
- [ ] **DOC-05**: The reference documents every preference in the prefs dialog with its default and effect.
- [ ] **DOC-06**: Markdown embeds the captured PNGs and renders correctly on GitHub.

### PDF Build (PDF)
- [ ] **PDF-01**: A pandoc + LaTeX build converts the markdown source into a single PDF.
- [ ] **PDF-02**: The PDF preserves document hierarchy (table of contents, nested sections) and embedded screenshots.
- [ ] **PDF-03**: The PDF is produced as a build artifact (not committed), suitable for attaching to a GitHub Release.

---

## Future Requirements (Deferred)

- CI integration of the doc build — deferred; requires a headless Nuke license, which the project does not have.
- HTML / web documentation target — markdown + PDF are sufficient for v1.5.

## Out of Scope

- Hosting docs on a website / ReadTheDocs — markdown renders on GitHub; PDF attaches to releases.
- Animated GIF or video capture — `nuke-docs-screenshotter` produces still PNGs only.
- Documenting internal/private functions — docs cover user-facing functionality, not the source API.

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BUILD-01 | Phase 22 | Pending |
| SCENE-01 | Phase 23 | Pending |
| SCENE-02 | Phase 23 | Pending |
| SCENE-03 | Phase 23 | Pending |
| SCENE-04 | Phase 23 | Pending |
| CAP-01 | Phase 23 | Pending |
| CAP-02 | Phase 24 | Pending |
| CAP-03 | Phase 24 | Pending |
| DOC-01 | Phase 25 | Pending |
| DOC-02 | Phase 25 | Pending |
| DOC-03 | Phase 25 | Pending |
| DOC-04 | Phase 25 | Pending |
| DOC-05 | Phase 25 | Pending |
| DOC-06 | Phase 25 | Pending |
| PDF-01 | Phase 26 | Pending |
| PDF-02 | Phase 26 | Pending |
| PDF-03 | Phase 26 | Pending |
| BUILD-02 | Phase 26 | Pending |
| BUILD-03 | Phase 26 | Pending |
