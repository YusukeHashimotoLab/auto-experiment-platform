#!/usr/bin/env python3
"""Recompute the dispensing-stability statistics reported in README.md.

Usage:
    python examples/dispensing_stability/stats.py [path/to/weight.csv]

Reads a one-column CSV (header ``weight``) of balance readings in grams and
prints n, mean, sample standard deviation (ddof=1), relative standard
deviation, min and max. Requires only the standard library and NumPy.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

DEFAULT_CSV = Path(__file__).resolve().parent / "weight.csv"


def load(path: Path) -> np.ndarray:
    """Load the ``weight`` column of *path* as a float array (grams)."""
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows or "weight" not in rows[0]:
        raise SystemExit(f"{path}: expected a CSV with a 'weight' column")
    return np.asarray([float(row["weight"]) for row in rows], dtype=float)


def summarise(values: np.ndarray) -> dict[str, float]:
    """n, mean, sample SD (ddof=1), RSD in %, min and max of *values*."""
    n = values.size
    mean = float(values.mean())
    # Sample standard deviation: sqrt( sum((x_i - mean)^2) / (n - 1) )
    sd = float(values.std(ddof=1))
    # Relative standard deviation: 100 * SD / mean
    rsd = 100.0 * sd / mean
    return {
        "n": n,
        "mean_g": mean,
        "sd_g": sd,
        "rsd_percent": rsd,
        "min_g": float(values.min()),
        "max_g": float(values.max()),
    }


def main(argv: list[str]) -> int:
    path = Path(argv[1]).expanduser() if len(argv) > 1 else DEFAULT_CSV
    stats = summarise(load(path))
    print(f"file : {path}")
    print(f"n    : {stats['n']}")
    print(f"mean : {stats['mean_g']:.4f} g")
    print(f"SD   : {stats['sd_g']:.4f} g   (sample, ddof=1)")
    print(f"RSD  : {stats['rsd_percent']:.3f} %  (100 * SD / mean)")
    print(f"min  : {stats['min_g']:.2f} g")
    print(f"max  : {stats['max_g']:.2f} g")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
