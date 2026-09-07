#!/usr/bin/env python3
"""Thin HTTP client for the running camera server (camera_server.py).

Provides the capture and control primitives that acquire.py builds on:
triggering a single photo, and reading/writing camera control values.
Camera control always goes through this HTTP API (not the device directly)
because on Windows, DirectShow holds the camera exclusively and only the
server process may open it; the same code path is used on macOS.
"""
import json
import urllib.request

import paths

SERVER = "http://localhost:8799"


def capture_photo():
    """Ask the running server to take a photo and return the saved file's path."""
    req = urllib.request.Request(f"{SERVER}/api/capture", method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        res = json.loads(r.read())
    if not res.get("ok"):
        raise RuntimeError(f"Capture failed: {res}")
    return paths.PHOTOS_DIR / res["file"]


def get_control(name: str):
    """Read a control value from the server (= the process that owns the camera).

    name is one of the control names exposed by camera_server.py
    (exposure/gain/focus/autoExposure/autoFocus/whiteBalance/autoWhiteBalance).
    """
    with urllib.request.urlopen(f"{SERVER}/api/controls", timeout=10) as r:
        state = json.loads(r.read())
    v = state.get(name)
    return v.get("value") if isinstance(v, dict) else v


def set_control(name: str, value) -> None:
    """Write a control value via the server. Raises RuntimeError on failure."""
    body = json.dumps({"name": name, "value": value}).encode()
    req = urllib.request.Request(f"{SERVER}/api/control", data=body,
                                 method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        res = json.loads(r.read())
    if not res.get("ok"):
        raise RuntimeError(f"Camera control failed ({name}={value}): {res}")
