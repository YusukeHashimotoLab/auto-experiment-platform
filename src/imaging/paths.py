"""Shared directory layout for the imaging module.

All modules import their data locations from here, so every entry point --
`camera_server.py` (which launches `acquire.py` as a subprocess), a manual
`python acquire.py`, or `make_panel.py` -- agrees on one data root no matter
which directory it was started from. Locations are anchored to this file,
never to the current working directory; only `IMAGING_DATA_DIR` moves them.

    IMAGING_DATA_DIR  (env var)  root for captured photos and analysis output.
                                 Default: <repo root>/imaging_data, i.e. the
                                 directory two levels above this module
                                 (git-ignored, outside the source package).
    UVC_UTIL          (env var)  path to the `uvc-util` binary used for camera
                                 control on macOS. Default: `uvc-util` on PATH,
                                 falling back to <module dir>/bin/uvc-util.
"""
import os
import shutil
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
REPO_ROOT = MODULE_DIR.parent.parent            # <repo>/src/imaging -> <repo>
CONFIG_DIR = MODULE_DIR / "config"
STATIC_DIR = MODULE_DIR / "static"
EXAMPLES_DIR = MODULE_DIR / "examples"

DATA_DIR = Path(os.environ.get("IMAGING_DATA_DIR", REPO_ROOT / "imaging_data")).resolve()
PHOTOS_DIR = DATA_DIR / "photos"       # raw captures from the camera server
OUT_DIR = DATA_DIR / "analysis"        # per-run analysis output (spectral_<timestamp>/)

CAMERA_REFERENCE = CONFIG_DIR / "camera_reference.json"
CAMERA_LOCAL = CONFIG_DIR / "camera_local.json"       # per-PC camera selection (git-ignored)
LIGHT_REFERENCE = CONFIG_DIR / "light_reference.json"


def uvc_util_path() -> str:
    """Return the `uvc-util` executable to use on macOS (not bundled; see README)."""
    env = os.environ.get("UVC_UTIL")
    if env:
        return env
    found = shutil.which("uvc-util")
    if found:
        return found
    return str(MODULE_DIR / "bin" / "uvc-util")


def resolve_input(path) -> Path:
    """Resolve a user-supplied input path (a run directory, typically).

    Tried in order: as given (absolute, or relative to the current working
    directory), then relative to this module's directory, then relative to
    the data root. This is what lets the same command line work from
    `src/imaging` and from the repository root, e.g.

        python make_panel.py examples/zif8_vial_5s
        python src/imaging/make_panel.py examples/zif8_vial_5s

    The path is returned unchanged (merely absolute) if none of the
    candidates exists, so the caller can report the name the user typed.
    """
    p = Path(path)
    if p.is_absolute():
        return p
    for base in (Path.cwd(), MODULE_DIR, DATA_DIR):
        cand = base / p
        if cand.exists():
            return cand
    return (Path.cwd() / p)


def ensure_dirs() -> None:
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
