#!/usr/bin/env python3
"""List the currently connected cameras (Windows / DirectShow).

A helper for deciding which camera to use for measurement on a PC with
multiple webcams attached. Cameras that share the same name (e.g. two units
of the same model) are distinguished by **DevicePath**.

Usage:

    .venv\\Scripts\\python.exe list_cameras.py
        Show the list (index / name / DevicePath / current selection).

    .venv\\Scripts\\python.exe list_cameras.py --snapshot
        Take one shot from each camera and save it under
        <IMAGING_DATA_DIR>/analysis/camera_probe/. Looking at the images
        makes it obvious which one is the measurement camera.
        **Stop camera_server.py first** (DirectShow holds the camera
        exclusively, so a camera already held by camera_server.py cannot be
        opened here).

Once you've decided, write it into config/camera_reference.json like this
(a substring match is fine):

    "win32_device_path": "b&191bf0f6"

To switch just for one run, use the environment variables SPT_CAMERA_PATH /
SPT_CAMERA_NAME instead.
"""
import argparse
import sys
from pathlib import Path

import hw
import paths

if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass


def snapshot(devices: list[dict], outdir: Path) -> None:
    """Take one shot from each camera and save it."""
    import cv2

    outdir.mkdir(parents=True, exist_ok=True)
    for d in devices:
        idx = d["index"]
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print(f"  index {idx}: cannot open "
                  f"(it may be held by camera_server.py)")
            continue
        try:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, hw.VIDEO_W)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, hw.VIDEO_H)
            last = None
            for _ in range(15):          # the first few frames can be black
                ok, frame = cap.read()
                if ok:
                    last = frame
            if last is None:
                print(f"  index {idx}: could not get a frame")
                continue
            ok, buf = cv2.imencode(".jpg", last)
            if not ok:
                print(f"  index {idx}: JPEG encoding failed")
                continue
            path = outdir / f"camera_{idx}.jpg"
            # cv2.imwrite silently fails to write to non-ASCII paths; encode
            # with cv2 and write the bytes with Python instead.
            path.write_bytes(buf.tobytes())
            print(f"  index {idx}: {path}")
        finally:
            cap.release()


def main() -> int:
    parser = argparse.ArgumentParser(description="List connected cameras (Windows)")
    parser.add_argument("--snapshot", action="store_true",
                        help="take one shot from each camera and save it under "
                             "analysis/camera_probe/ (stop camera_server.py first)")
    args = parser.parse_args()

    if sys.platform != "win32":
        print("This script is Windows-only.")
        return 1

    devices = hw.list_win_cameras_detailed()
    if not devices:
        print("No cameras were detected.")
        return 1

    want_path = hw.win_camera_path()
    want_name = hw.win_camera_name()
    print(f"Selector: " + (f"path '{want_path}'" if want_path else f"name '{want_name}'"))
    print()
    for d in devices:
        print(f"  [index {d['index']}] {d['name']}")
        print(f"      path: {d['path']}")
    print()

    try:
        chosen = hw.resolve_win_camera()
        print(f"-> Camera to use: index {chosen['index']} '{chosen['name']}'")
    except RuntimeError as e:
        print(f"-> Cannot resolve a single camera:\n   {e}")

    if args.snapshot:
        outdir = paths.OUT_DIR / "camera_probe"
        print()
        print(f"Taking one shot from each camera -> {outdir}")
        snapshot(devices, outdir)
        print()
        print("Once you've picked the measurement camera from the images, put part")
        print('of its path into "win32_device_path" in config/camera_reference.json.')
    return 0


if __name__ == "__main__":
    sys.exit(main())
