#!/usr/bin/env python3
"""Vial geometry feature extraction.

Extracts container / liquid-level / suspension features from a backlit photo
of a screw-cap centrifuge vial and writes them out as JSON.

Usage:
    python3 geometry.py photos/sample_20260711_105606.jpg
    python3 geometry.py photos/sample_20260711_105606.jpg --out analysis
    -> writes <out>/<name>_features.json (default --out: paths.OUT_DIR)
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

from paths import OUT_DIR

BRIGHT = 170          # luminance threshold for "white liquid / cap"
BG = 60               # luminance threshold for background (blackout curtain)
MIN_SEG_ROWS = 10     # minimum row count for a vertical segment (noise rejection)


def luminance(rgb: np.ndarray) -> np.ndarray:
    return rgb @ np.array([0.299, 0.587, 0.114])


def find_vial_columns(gray: np.ndarray, y0: int = 0, y1: int | None = None,
                      thr: float = BG, frac: float = 0.35) -> tuple[int, int]:
    """Find the left/right edges of the bright vertical band near the image
    center, within the given row range."""
    h, w = gray.shape
    col_frac = (gray[y0:y1] > thr).mean(axis=0)
    bright_cols = col_frac > frac
    cx = w // 2
    if not bright_cols[cx]:  # if the center is dark, jump to the nearest bright column
        idx = np.flatnonzero(bright_cols)
        if idx.size == 0:
            raise ValueError("No vial found (no bright region)")
        cx = idx[np.abs(idx - cx).argmin()]
    x0 = cx
    while x0 > 0 and bright_cols[x0 - 1]:
        x0 -= 1
    x1 = cx
    while x1 < w - 1 and bright_cols[x1 + 1]:
        x1 += 1
    return x0, x1


def bright_segments(profile: np.ndarray, thr: float) -> list[tuple[int, int]]:
    """Return contiguous runs [(y0, y1), ...] in a 1-D profile that exceed thr."""
    mask = profile > thr
    segs, start = [], None
    for i, m in enumerate(mask):
        if m and start is None:
            start = i
        elif not m and start is not None:
            if i - start >= MIN_SEG_ROWS:
                segs.append((start, i - 1))
            start = None
    if start is not None and len(mask) - start >= MIN_SEG_ROWS:
        segs.append((start, len(mask) - 1))
    return segs


def extract_features(path: Path) -> dict:
    img = Image.open(path).convert("RGB")
    rgb = np.asarray(img, dtype=np.float64)
    gray = luminance(rgb)
    h, w = gray.shape

    # ---- horizontal position of the vial ----
    x0, x1 = find_vial_columns(gray)
    vial_w = x1 - x0 + 1

    # vertical structure is judged from the vertical profile of the center
    # band (middle third of the vial width)
    bx0 = x0 + vial_w // 3
    bx1 = x1 - vial_w // 3
    band = gray[:, bx0:bx1 + 1]
    profile = band.mean(axis=1)

    # thresholds are derived from the profile's own measured values so this
    # still works across different exposures
    bg_lv = float(np.percentile(profile, 5))
    peak = float(np.percentile(profile, 99))
    rng = max(peak - bg_lv, 1e-6)
    thr_bright = max(bg_lv + 0.55 * rng, 0.75 * peak)
    thr_cap = bg_lv + 0.15 * rng    # mid-luminance threshold for dark-cap detection
    thr_tail = bg_lv + 0.25 * rng   # for tracking the vignetted lower liquid region

    segs = bright_segments(profile, thr_bright)
    if not segs:
        raise ValueError("No bright segment found")

    # topmost bright block = cap, largest bright block = liquid
    cap = segs[0]
    liquid = max(segs, key=lambda s: s[1] - s[0])
    if liquid == cap and len(segs) > 1:
        liquid = max(segs[1:], key=lambda s: s[1] - s[0])
    # If the cap is a dark color, the first bright segment is actually the
    # glass shoulder just below the cap. If there is a "dark background ->
    # mid-luminance band" pattern above it, treat that band as the cap
    # instead. (If what is above the band is not background, it is backlight
    # bleed, so it is not treated as the cap.)
    above = np.flatnonzero(profile[:cap[0]] > thr_cap)
    if (above.size >= MIN_SEG_ROWS and cap[0] - above[0] >= MIN_SEG_ROWS
            and above[0] >= MIN_SEG_ROWS
            and float(profile[:above[0]].mean()) < bg_lv + 0.05 * rng):
        cap = (int(above[0]), cap[0] - 1)
    cap_y0, cap_y1 = cap
    # once the cap is finalized, re-pick the liquid segment as the largest
    # bright segment below the cap (the original candidate can be wrong if
    # the cap was reassigned above)
    below = [s for s in segs if s[0] > cap_y1]
    if below:
        liquid = max(below, key=lambda s: s[1] - s[0])
    liq_y0, liq_y1 = liquid

    # extend the lower liquid boundary through the mid-luminance vignetted
    # region caused by backlight falloff, as long as it continues
    while liq_y1 + 1 < h and profile[liq_y1 + 1] > thr_tail:
        liq_y1 += 1

    # At a bright exposure, the headspace directly viewing the backlight can
    # saturate and merge into one continuous bright segment with the liquid.
    # If there is a run of saturated rows in the upper half of the segment,
    # that is the headspace glow; treat the luminance transition at its
    # lower edge as the meniscus and split the segment there.
    SAT_LV = 250.0
    seg_prof = profile[liq_y0:liq_y1 + 1]
    # condensation etc. can create a short fragment before the saturated
    # region, so use the largest run in the upper half (not simply the first
    # run) as the true glow
    sat_runs = [r for r in bright_segments(seg_prof, SAT_LV)
                if r[0] < len(seg_prof) // 2]
    sat = max(sat_runs, key=lambda r: r[1] - r[0], default=None)
    if sat is not None:
        y = liq_y0 + sat[1]
        # the meniscus is where the sharp luminance drop right after
        # saturation (the transition band) has fully descended
        while y + 1 < liq_y1 and profile[y + 1] < profile[y] - 1.0:
            y += 1
        if liq_y1 - (y + 1) >= MIN_SEG_ROWS:
            liq_y0 = y + 1

    # In samples with a clear supernatant over a bright sediment layer, the
    # supernatant's attenuation keeps the headspace glow from merging with
    # the liquid segment, so it becomes a separate segment and "largest
    # segment = liquid" only captures the sediment layer, missing the
    # meniscus. If there is a saturated glow segment between the cap and the
    # liquid, apply the same rule: descend through the luminance transition
    # at its lower edge and use that as the new top of the liquid segment.
    glows = [s for s in segs
             if s[0] > cap_y1 and s[1] < liq_y0
             and (profile[s[0]:s[1] + 1] >= SAT_LV).sum() >= MIN_SEG_ROWS]
    if glows:
        y = glows[-1][1]
        while y + 1 < liq_y1 and profile[y + 1] < profile[y] - 1.0:
            y += 1
        if y + 1 < liq_y0:
            liq_y0 = y + 1

    # width of the glass body alone: look for bright columns in the rows
    # where the (white) liquid is visible (the cap is wider than the body,
    # and the dark gap beside the body can exceed the background threshold)
    body_thr = 0.7 * float(profile[liq_y0:liq_y1 + 1].mean())
    body_x0, body_x1 = find_vial_columns(gray, y0=liq_y0, y1=liq_y1 + 1,
                                         thr=body_thr, frac=0.6)

    # headspace (cap bottom to meniscus)
    head_y0, head_y1 = cap_y1 + 1, liq_y0 - 1

    # fill fraction relative to the body (cap bottom to liquid bottom)
    body_h = liq_y1 - cap_y1
    fill_fraction = (liq_y1 - liq_y0 + 1) / body_h if body_h > 0 else None

    # ---- liquid region features ----
    liq_rgb = rgb[liq_y0:liq_y1 + 1, x0:x1 + 1]
    liq_gray = gray[liq_y0:liq_y1 + 1, x0:x1 + 1]
    r, g, b = liq_rgb[..., 0].mean(), liq_rgb[..., 1].mean(), liq_rgb[..., 2].mean()
    mx = liq_rgb.max(axis=2)
    mn = liq_rgb.min(axis=2)
    saturation = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)

    # vertical luminance profile -> sedimentation indicator (top/bottom
    # luminance difference)
    liq_profile = liq_gray.mean(axis=1)
    n3 = max(1, len(liq_profile) // 3)
    top_third = float(liq_profile[:n3].mean())
    bottom_third = float(liq_profile[-n3:].mean())

    # meniscus sharpness: max luminance gradient around the meniscus
    g0 = max(0, liq_y0 - 15)
    # the meniscus can go either "dark -> bright" (dark headspace) or
    # "bright -> dark" (glowing headspace), so evaluate the absolute gradient
    grad = np.diff(profile[g0:liq_y0 + 15])
    meniscus_sharpness = float(np.abs(grad).max()) if grad.size else None

    return {
        "file": str(path),
        "analyzed_at": datetime.now().isoformat(timespec="seconds"),
        "image_size": {"width": w, "height": h},
        "vial": {"x0": int(x0), "x1": int(x1), "width_px": int(vial_w)},
        "body": {"x0": int(body_x0), "x1": int(body_x1),
                 "width_px": int(body_x1 - body_x0 + 1)},
        "cap": {"y0": int(cap_y0), "y1": int(cap_y1),
                "height_px": int(cap_y1 - cap_y0 + 1)},
        "headspace": {
            "y0": int(head_y0), "y1": int(head_y1),
            "height_px": int(max(0, head_y1 - head_y0 + 1)),
            "mean_luminance": round(float(gray[head_y0:head_y1 + 1,
                                               bx0:bx1 + 1].mean()), 2)
            if head_y1 >= head_y0 else None,
        },
        "liquid": {
            "top_y": int(liq_y0), "bottom_y": int(liq_y1),
            "height_px": int(liq_y1 - liq_y0 + 1),
            "fill_fraction_of_body": round(fill_fraction, 4),
            "mean_rgb": [round(r, 2), round(g, 2), round(b, 2)],
            "mean_luminance": round(float(liq_gray.mean()), 2),
            "luminance_std": round(float(liq_gray.std()), 2),
            "mean_saturation": round(float(saturation.mean()), 4),
            "top_third_luminance": round(top_third, 2),
            "bottom_third_luminance": round(bottom_third, 2),
            "sedimentation_index": round(bottom_third - top_third, 2),
        },
        "meniscus": {"y": int(liq_y0),
                     "sharpness": round(meniscus_sharpness, 2)
                     if meniscus_sharpness is not None else None},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photo", type=Path, help="Path to a white backlit photo")
    ap.add_argument("--out", type=Path, default=OUT_DIR,
                    help=f"Output directory for <stem>_features.json (default: {OUT_DIR})")
    args = ap.parse_args()

    feat = extract_features(args.photo)
    args.out.mkdir(parents=True, exist_ok=True)
    json_path = args.out / f"{args.photo.stem}_features.json"
    json_path.write_text(json.dumps(feat, indent=2, ensure_ascii=False),
                         encoding="utf-8")
    print(json.dumps(feat, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
