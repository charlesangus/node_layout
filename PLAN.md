---
title: Node Layout user guide PDF
status: done
current: null
pm_heartbeat: 2026-07-08T03:25:00+00:00
ship: pr-per-milestone
---

# Goal

Produce a print-friendly **Node Layout user guide** as `docs/user-guide.pdf`,
built with `make pdf` from a standalone `docs/user-guide.md` through pandoc +
the existing `docs/latex/trainingDoc.cls`, styled like the labelmaker/anchors
guides. Headline features are illustrated with **before/after** DAG images whose
"after" state is produced by actually running the real Node Layout commands
(headless via `nuke -t`) on a copy of a messy graph, all kept in as few
hand-editable `.nk` fixtures as possible and rendered to PNG via
nuke-screenshotter. Make Room is covered first; remaining headline features
(Layout Upstream, Layout Selected, Layout Selected Horizontal, Freeze/Unfreeze,
Shrink/Expand) each get a before/after pair; the leader window and preferences
dialog get GUI captures; everything else is summarized in an "Other Features"
section without required imagery. Done when `make pdf` yields a complete,
readable PDF with all headline images embedded and current.

# Context and constraints

- **Analog projects.** `charlesangus/anchors` is the closest model: a standalone
  `docs/user-guide.md` → pandoc (`--defaults docs/pandoc/pdf.yaml`, a
  `float-images.lua` filter, `TEXINPUTS` pointing at `docs/latex`) → PDF, with a
  `make screenshots` step that drives nuke-screenshotter over committed `.nk`
  fixtures and a `gui.json` playback scenario. `charlesangus/labelmaker` uses the
  same pandoc/`trainingDoc.cls` toolchain but derives its guide from README; we
  are NOT doing that — this guide is authored standalone.
- **Already present in this repo.** `docs/latex/trainingDoc.cls` and
  `docs/latex/logo.pdf` are already copied in (the only pre-existing "started
  work" — adopt them as-is). `pandoc`, `xelatex`/`pdflatex`/`lualatex`, `make`,
  and a `nuke` binary are all installed locally. Existing `.nk` fixtures live in
  `nuke_tests/fixtures/` and can seed the "messy graph" source material.
- **nuke-screenshotter (`charlesangus/nuke-screenshotter`, package
  `nuke-docs-screenshotter`) is the user's own repo, installable and confirmed
  working in this environment.** It is not yet installed — clone and
  `pip install .` into the venv before image steps run. It has three
  modes: **backdrop** (render one PNG per `screenshot:`-labelled BackdropNode in
  a `.nk`), **playback** (drive live UI interactions from a scenario `.json`),
  and **widget capture** (`exec` a `.py` and capture named Qt widgets). It drives
  a real Nuke GUI under a virtual framebuffer (xvfb), so PNG *rendering* needs a
  GUI/xvfb even though our `.nk` *generation* is headless.
- **Two-stage image model.** (1) A headless `nuke -t` "fixture builder" script
  constructs a messy source graph, copies it, runs the real Node Layout command
  on the copy, and lays out a `screenshot:<name>-before` and
  `screenshot:<name>-after` BackdropNode around each region, saving a combined
  `.nk`. Keep as much as possible in ONE `.nk` per feature group so it stays
  hand-editable. (2) `make screenshots` runs screenshotter backdrop mode over the
  committed `.nk`(s) → PNGs in `docs/images/`.
- **Real command entry points** (all operate on `nuke.selectedNodes()` and mutate
  `xpos`/`ypos`, so they run under `nuke -t`): `node_layout.layout_upstream()`,
  `node_layout.layout_selected()`, `node_layout.layout_selected_horizontal()`,
  `node_layout.freeze_selected()` / `unfreeze_selected()`,
  `node_layout.shrink_selected()` / `expand_selected()`,
  `make_room.make_room(amount, direction)`. The leader overlay
  (`node_layout_leader` / `node_layout_overlay`) and prefs dialog
  (`node_layout_prefs_dialog`) are GUI-only and must be captured via
  screenshotter playback/widget mode, not `nuke -t`.
- **DAG coordinate system:** positive Y is DOWN, negative Y is UP; upstream nodes
  sit at lower Y. Keep this in mind when authoring fixtures and backdrop bounds.
- **Constraints:** GPL-3.0 project; no machine-local absolute paths anywhere
  (parameterize the screenshotter clone path and Nuke path via Make variables /
  env vars). Descriptive names. No Co-Authored-By lines in commits.

# Milestones

## Milestone 1: PDF build harness

Stand up the standalone-guide toolchain end to end so every later milestone only
adds content. Reuse the already-present `trainingDoc.cls` + `logo.pdf`.

### Phase 1.1: Pandoc pipeline

- [x] M1.P1.T1 — Add pandoc build config and float filter
  - files: docs/pandoc/pdf.yaml (new), docs/pandoc/float-images.lua (new)
  - approach: mirror the anchors setup — `pdf.yaml` sets pdf-engine
    (xelatex), `documentclass: trainingDoc`, a resource path, and standard margins;
    `float-images.lua` forces `[H]` figure placement. Reference `trainingDoc.cls`
    by class name; do not restyle the class.
  - verify: `pandoc --defaults docs/pandoc/pdf.yaml --lua-filter docs/pandoc/float-images.lua`
    parses without error against a one-line test markdown.
  - size: M
- [x] M1.P1.T2 — Add a stub standalone guide with title metadata
  - files: docs/user-guide.md (new)
  - approach: YAML metadata block (title "Node Layout — User Guide", author,
    the logo via `trainingDoc.cls` conventions) plus a short intro paragraph and
    empty placeholder headings for Make Room and the headline features. No images
    yet.
  - verify: file parses as valid pandoc markdown; headings present.
  - size: S

### Phase 1.2: Make target

- [x] M1.P2.T1 — Add `make pdf` target producing docs/user-guide.pdf
  - files: Makefile (new), .gitignore (edit)
  - approach: `pdf` target invokes pandoc with `TEXINPUTS` including
    `docs/latex`, the `--defaults`/`--lua-filter`/`--resource-path` flags, input
    `docs/user-guide.md`, output `docs/user-guide.pdf`. Add a `build/` scratch dir
    if needed and gitignore transient artefacts. Use Make variables (no absolute
    paths).
  - verify: `make pdf` exits 0 and `docs/user-guide.pdf` opens as a valid PDF
    containing the stub headings and logo.
  - size: M

**Milestone 1 verification gate:** `make pdf` builds `docs/user-guide.pdf` from
the stub `docs/user-guide.md` using `trainingDoc.cls`, with no absolute paths in
the Makefile or pandoc config.

## Milestone 2: Image pipeline proven on Make Room

Prove the full two-stage image pipeline (headless `.nk` generation →
screenshotter PNG render) end to end on the required-first feature, Make Room.

### Phase 2.1: Screenshotter environment

- [x] M2.P1.T1 — Add reproducible screenshotter setup
  - files: docs/README-build.md (new), Makefile (edit)
  - approach: document + script cloning `charlesangus/nuke-screenshotter` and
    `pip install .` into the venv, and running under xvfb. Expose the
    screenshotter dir and Nuke binary as overridable Make variables / env vars
    (e.g. `SCREENSHOTTER_DIR ?= …`, `NUKE ?= nuke`) — no hardcoded local paths.
  - verify: following docs/README-build.md on a clean venv makes
    `nuke_dag_capture_auto --help` succeed (the installed console command).
  - size: M

### Phase 2.2: Make Room before/after

- [x] M2.P2.T1 — Headless fixture builder for Make Room before/after
  - files: docs/screenshots/build_dag_fixtures.py (new)
  - approach: a `nuke -t`-run script that builds a small messy cluster, copies
    it, calls `make_room.make_room(amount, direction)` on the copy, and wraps a
    `screenshot:make-room-before` and `screenshot:make-room-after` BackdropNode
    around each region (respect Y-down). Save to
    docs/screenshots/fixtures/make_room.nk. Keep both states in the one `.nk`.
  - verify: `nuke -t docs/screenshots/build_dag_fixtures.py` writes
    make_room.nk containing two `screenshot:`-labelled backdrops.
  - size: M
- [x] M2.P2.T2 — `make screenshots` renders Make Room PNGs via backdrop mode
  - files: Makefile (edit)
  - approach: add a `screenshots` target that runs screenshotter backdrop mode
    over docs/screenshots/fixtures/*.nk under xvfb, emitting PNGs to
    docs/images/. Make `pdf` depend on images being present (but not force a
    Nuke run on every pdf build — keep them separate targets).
  - verify: `make screenshots` produces docs/images/make_room_before.png and
    make_room_after.png that visibly differ. (The screenshotter slugifies the
    `screenshot:make-room-*` labels to underscore filenames.)
  - size: M
- [x] M2.P2.T3 — Write the Make Room guide section with its images
  - files: docs/user-guide.md (edit)
  - approach: replace the Make Room placeholder with prose (headline framing,
    shortcuts table, with/without-selection behaviour) and a before/after figure
    pair referencing docs/images/make_room_*.png. Place this section first.
  - verify: `make pdf` embeds both Make Room images and the section renders first.
  - size: S

**Milestone 2 verification gate:** `make screenshots && make pdf` yields a PDF
whose first feature section is Make Room with a genuine before/after pair
rendered from a tool-produced `.nk`; the pipeline is documented and repeatable.

## Milestone 3: Headline DAG feature before/after content

Author before/after pairs and guide sections for the remaining headline
DAG-transformation commands, reusing the M2 pipeline.

### Phase 3.1: Fixtures for the layout commands

- [x] M3.P1.T1 — Add Layout Upstream and Layout Selected fixtures
  - files: docs/screenshots/build_dag_fixtures.py (edit)
  - approach: extend the builder with two scenarios — a messy upstream tree run
    through `node_layout.layout_upstream()`, and a multi-root selection run
    through `node_layout.layout_selected()` — each producing
    `screenshot:*-before`/`*-after` backdrops. Seed from an existing
    nuke_tests/fixtures/*.nk where suitable.
  - verify: `nuke -t …build_dag_fixtures.py` emits the four new backdrops; `make
    screenshots` renders four PNGs.
  - size: M
- [x] M3.P1.T2 — Add Layout Selected Horizontal and Freeze/Unfreeze fixtures
  - files: docs/screenshots/build_dag_fixtures.py (edit)
  - approach: add a horizontal-spine scenario via
    `node_layout.layout_selected_horizontal()`, and a freeze scenario that pins a
    node with `node_layout.freeze_selected()` then lays out around it — showing
    the frozen node staying put. Emit before/after backdrops for each.
  - verify: `make screenshots` renders the horizontal and freeze before/after
    PNGs; the freeze "after" shows the pinned node unmoved.
  - size: M
- [x] M3.P1.T3 — Add Shrink/Expand fixture
  - files: docs/screenshots/build_dag_fixtures.py (edit)
  - approach: build a laid-out tree, capture "before", call
    `node_layout.shrink_selected()` (and/or `expand_selected()`) on the copy,
    capture "after" showing the centred scale. Emit before/after backdrops.
  - verify: `make screenshots` renders shrink/expand before/after PNGs that
    differ in spread.
  - size: S

### Phase 3.2: Guide sections

- [x] M3.P2.T1 — Write the layout-command guide sections with images
  - files: docs/user-guide.md (edit)
  - approach: add reader-oriented sections for Layout Upstream, Layout Selected,
    Layout Selected Horizontal, Freeze/Unfreeze, and Shrink/Expand, each with its
    before/after figure pair and the relevant shortcuts. Keep the anchors-style
    tutorial framing.
  - verify: `make pdf` embeds all five sections' images and reads coherently.
  - size: M

**Milestone 3 verification gate:** `make screenshots && make pdf` produces a PDF
in which every headline DAG command has a working, tool-produced before/after
figure pair and prose.

## Milestone 4: GUI captures — leader window and preferences

Capture the two GUI-only features via screenshotter's playback/widget modes and
add their sections.

### Phase 4.1: GUI scenarios

- [x] M4.P1.T1 — Leader window overlay capture scenario
  - files: docs/screenshots/gui/leader.json (new) OR docs/screenshots/gui/leader_capture.py (new)
  - approach: author a screenshotter playback scenario (or widget-capture `.py`)
    that arms leader mode (`node_layout_leader.arm()`), waits for the overlay
    (`node_layout_overlay`), and captures it to docs/images/leader-window.png.
  - verify: running the scenario under xvfb produces a leader-window.png showing
    the HUD with the key badges.
  - size: M
- [x] M4.P1.T2 — Preferences dialog capture scenario
  - files: docs/screenshots/gui/prefs.json (new) OR docs/screenshots/gui/prefs_capture.py (new)
  - approach: open `node_layout_prefs_dialog` and capture the dialog widget to
    docs/images/preferences-dialog.png via widget-capture mode.
  - verify: running the scenario under xvfb produces preferences-dialog.png
    showing the real dialog controls.
  - size: M
- [x] M4.P1.T3 — Wire GUI captures into `make screenshots`
  - files: Makefile (edit)
  - approach: add gui-shots sub-steps that invoke screenshotter playback/widget
    mode over the leader and prefs scenarios, emitting into docs/images/. Keep
    variable-driven, xvfb-wrapped, no absolute paths.
  - verify: `make screenshots` (re)generates leader-window.png and
    preferences-dialog.png alongside the DAG PNGs.
  - size: S

### Phase 4.2: Guide sections

- [x] M4.P2.T1 — Write the Leader Window and Preferences sections with images
  - files: docs/user-guide.md (edit)
  - approach: add sections for the leader window (key colour-coding, command
    table, click-to-dispatch) and the preferences dialog (each configurable
    group), each embedding its captured PNG.
  - verify: `make pdf` embeds both GUI images and the sections render correctly.
  - size: S

**Milestone 4 verification gate:** `make screenshots && make pdf` yields a PDF
whose Leader Window and Preferences sections carry real GUI captures produced by
screenshotter.

## Milestone 5: Other Features section and final polish

Complete the guide with the text-only "Other Features" coverage and a final
editorial/visual pass.

### Phase 5.1: Remaining coverage

- [x] M5.P1.T1 — Write the "Other Features" section
  - files: docs/user-guide.md (edit)
  - approach: concise subsections (no required images) for Compact/Loose
    variants, Clear Layout State, Diamond Resolution, Select Upstream Ignoring
    Hidden, Sort By Filename, and Safe Delete — each a short paragraph plus
    shortcut/behaviour notes, consistent with the headline sections.
  - verify: `make pdf` renders the Other Features section with all six topics.
  - size: S

### Phase 5.2: Polish

- [x] M5.P2.T1 — Front matter, intro, and cross-references
  - files: docs/user-guide.md (edit)
  - approach: add a short "What is Node Layout" intro, a coordinate-system note,
    and a features overview / table of contents; ensure Make Room leads the
    feature sections and figure captions are consistent. No install section
    (guide is install-free like labelmaker's).
  - verify: `make pdf` produces a coherent front-to-back reading order with a ToC.
  - size: S
- [x] M5.P2.T2 — Final PDF review and image freshness pass
  - files: docs/user-guide.md (edit), docs/images/ (regenerate)
  - approach: run `make screenshots && make pdf` clean; visually check every
    figure is current and legible, fix any overflow/float issues, and confirm no
    stale images remain. Update README with a one-line pointer to the guide + how
    to build it.
  - verify: a clean `make screenshots && make pdf` produces the final
    docs/user-guide.pdf with all sections and current images; visual review passes.
  - size: M

**Milestone 5 verification gate:** a clean `make screenshots && make pdf` builds
the complete, polished `docs/user-guide.pdf` — Make Room first, all headline
before/after pairs and GUI captures current, Other Features covered — with no
absolute paths and README pointing to it.

# Decisions

- 2026-07-07 — Author a standalone `docs/user-guide.md` (anchors model) rather
  than deriving the guide from README (labelmaker model): the guide can be
  structured as a reader tutorial with before/after callouts instead of tracking
  the README's reference structure. (User decision.)
- 2026-07-07 — Produce before/after DAG images by running the real Node Layout
  commands headlessly with `nuke -t` on a copied messy graph, keeping both states
  in as few hand-editable `.nk` fixtures as possible; render PNGs from those
  `.nk`s with nuke-screenshotter backdrop mode. GUI-only features (leader
  overlay, prefs dialog) use screenshotter playback/widget capture. (User
  decision.)
- 2026-07-07 — Coverage is curated to headline features with before/after images
  (Make Room FIRST, then Layout Upstream, Layout Selected, Layout Selected
  Horizontal, Freeze/Unfreeze, Shrink/Expand, plus leader window and
  preferences); all other features go in a text-only "Other Features" section.
  (User decision.)
- 2026-07-07 — Adopt the pre-existing `docs/latex/trainingDoc.cls` + `logo.pdf`
  as-is; the only prior "started work" was these two copied files.
- 2026-07-07 (M1.P1.T1) — Renamed `docs/latex/training_doc.cls` →
  `trainingDoc.cls` (content unchanged) so `\documentclass{trainingDoc}` resolves
  by filename without a build-time symlink. Set `fontfamily: mathptmx` in
  `docs/pandoc/pdf.yaml` because this environment lacks `lmodern.sty` and pandoc's
  default LaTeX template loads it unless `fontfamily` is set; keeps `make pdf`
  self-sufficient with no CLI flags.
- 2026-07-07 (M1.P2.T1) — Gitignore the generated `docs/user-guide.pdf` (a
  regenerable `make pdf` artifact) rather than commit it, to avoid binary churn
  as images change each milestone; `docs/latex/logo.pdf` stays tracked.

- 2026-07-07 (M2.P1.T1) — Screenshotter facts confirmed by inspecting the repo:
  install via `pip install .` (zero runtime deps, py>=3.9); the console command is
  `nuke_dag_capture_auto` (smart input by extension: `.nk`→backdrop, `.json`→
  playback, `.py`→widget); it launches Nuke itself wrapped in `xvfb-run` (pass
  `--no-xvfb` to use an existing `$DISPLAY`), finds Nuke via `--nuke-exec` / `NUKE`
  env / `which nuke`, sets `LIBGL_ALWAYS_SOFTWARE=1`+`GALLIUM_DRIVER=llvmpipe`, and
  needs Mesa software-GL (present here) + an interactive Nuke license (GUI mode,
  not `--tg`). Backdrop mode removes `screenshot:` marker backdrops before capture
  by default (`--show-backdrop` to keep them); never modifies the `.nk` on disk.

- 2026-07-07 (M3.P1.T2) — Freeze only preserves a MULTI-node block's internal
  offsets during layout; a lone frozen node is a no-op (verified via
  tests/test_freeze_integration.py Scenario B + `nuke -t` trials). The Freeze
  figure therefore freezes a 2-node Grade+Merge block with a hand-set side
  offset and shows the ENGINE keeping that offset while non-frozen nodes tidy —
  no fabricated positions. Also: `freeze_selected()` writes a random `uuid4` into
  the `.nk`, so the builder patches `uuid.uuid4` with a deterministic counter (as
  with the other `nuke -t` patches) to keep `freeze.nk` byte-reproducible.

- 2026-07-07 (M3.P1.T3) — Shrink/Expand scale is anchored on the most-downstream
  selected node (which stays fixed), not the selection's bounding-box midpoint —
  verified against `_scale_selected_nodes` in the engine. The shrink fixture uses
  a tidy two-branch tree and asserts both spreads shrink and the anchor is
  unmoved; guide prose (M3.P2.T1) should describe the behaviour as anchor-centred,
  not "centred on the selection".

- 2026-07-08 (M4.P1.T1) — Leader HUD captured via screenshotter WIDGET mode
  (docs/screenshots/gui/leader_capture.py), constructing `LeaderKeyOverlay`
  directly instead of `node_layout_leader.arm()`: the overlay populates fully in
  `__init__` and arm() needs a focused DAG panel + prefs timer that are
  non-deterministic under xvfb; the rendered widget is identical. Playback mode
  was unsuitable because the overlay sets no Qt objectName.

- 2026-07-08 (M5.P2.T2) — Fixed four figures that rendered at natural pixel
  size and overflowed the page by adding `max width=\linewidth, max
  height=0.8\textheight` (adjustbox export keys, already loaded by
  trainingDoc.cls) in float-images.lua for images without explicit dimensions —
  scale-down only, so correctly-sized figures are untouched.

# Open questions

- Minor source-comment drift found while writing M4.P2.T1 (not fixed — outside
  this docs plan's scope): `node_layout_leader.py`'s module docstring claims
  leader mode is armed by `Shift+E`, but `menu.py` actually binds `Shift+D`
  (`Shift+E` is Layout Upstream). The guide documents the correct `Shift+D`.
  A one-line docstring fix could ride any future code PR.
- None otherwise outstanding. (nuke-screenshotter is the user's own repo, installable and
  confirmed working in this environment, so the image milestones run end to end
  here — no human/UAT fallback needed for PNG rendering.)
