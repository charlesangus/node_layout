# Build setup

This document covers the tooling used to build project documentation:
rendering the PDF user guide, and capturing Nuke DAG screenshots for the
docs.

## PDF user guide

`make pdf` renders `docs/user-guide.md` into `docs/user-guide.pdf` via
pandoc. See the comments at the top of the `Makefile` for details. This
section is unaffected by anything below.

## Documentation screenshotter

`make screenshots` renders PNG screenshots of Nuke node graphs for the docs
using [`nuke-docs-screenshotter`](https://github.com/charlesangus/nuke-screenshotter)
(console command `nuke_dag_capture_auto`). This tool is a separate,
GPL-licensed project — it is **not vendored** into this repository. Instead
it is cloned on demand into a gitignored directory and installed locally.

### Prerequisites

- **Nuke, with an interactive (GUI) license.** The tool launches a real Nuke
  process in GUI mode to render captures; a render-only/non-interactive
  license will not work. The `nuke` binary must be resolvable via one of:
  - the `--nuke-exec <path>` flag,
  - the `NUKE` environment variable, or
  - `nuke` being on `$PATH` (this is already the case in this environment).
- **`xvfb-run`.** By default the tool wraps its Nuke invocation in
  `xvfb-run` so it can run headless without a real X display. Pass
  `--no-xvfb` to use an existing `$DISPLAY` instead.
- **Mesa software rendering (llvmpipe).** The tool automatically sets
  `LIBGL_ALWAYS_SOFTWARE=1` and `GALLIUM_DRIVER=llvmpipe` so Nuke's OpenGL
  usage works without a GPU. No extra configuration is needed as long as
  Mesa is installed.
- **Python >= 3.9** with `pip`. The package itself has zero runtime pip
  dependencies.

### Installing

Run:

```sh
make screenshotter-setup
```

This target:

1. Clones `SCREENSHOTTER_REPO` into `SCREENSHOTTER_DIR` if it isn't already
   present there (if it is, it runs `git pull` instead, so the target is
   idempotent and safe to re-run).
2. Runs `pip install` against that clone, which installs the
   `nuke-docs-screenshotter` package and exposes the `nuke_dag_capture_auto`
   console command.

Both the repo URL, the clone location, the `nuke` binary to use, and the
`pip`/install-flags to use are overridable Make variables (see the top of
`Makefile`), for example:

```sh
make screenshotter-setup SCREENSHOTTER_DIR=build/nuke-screenshotter PIP=pip
```

By default the clone lives under `.tools/nuke-screenshotter`, which is
gitignored, and the install uses `pip3 install --user --break-system-packages`.
The `--user` flag puts the `nuke_dag_capture_auto` command in the current
user's local bin directory (e.g. `~/.local/bin`), and `--break-system-packages`
is needed on Debian/Ubuntu systems where the system Python is "externally
managed" (PEP 668) and refuses `--user` installs otherwise. If your
`pip`/`PATH` setup differs (e.g. you want to install into a virtualenv
instead), override `PIP` and `PIP_INSTALL_ARGS` accordingly and make sure
the resulting install location is on `$PATH`.

Verify the install with:

```sh
nuke_dag_capture_auto --help
```

### Invocation

`nuke_dag_capture_auto` picks its capture mode from the input file's
extension:

- `.nk` — backdrop mode
- `.json` — playback mode
- `.py` — widget mode

Basic usage:

```sh
nuke_dag_capture_auto <input> <output-dir>
```

`make screenshots` drives this tool over this project's committed `.nk`
fixtures under `docs/screenshots/fixtures/`, rendering PNGs into
`docs/images/`. It remains independent of `make pdf`, which never invokes
Nuke. Further feature fixtures are added by later milestone tasks.
