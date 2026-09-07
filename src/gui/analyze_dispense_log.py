#!/usr/bin/env python
"""Precision / accuracy statistics for a dispensing run.

Reads the CSV artefacts of one run folder (``logs/<date>/<name>_<timestamp>/``)
written by :class:`~src.flow.experiment_logger.ExperimentLogger` and
:class:`~src.flow.accuracy_logger.DispenseAccuracyLogger`, and reports the
statistics used in the paper: mean, standard deviation, variance, CV
(repeatability) and the bias against the nominal dispensed mass (trueness).

Two sources, in this order:

1. ``dispense_accuracy.csv`` - one row per ``dispense`` paired with the
   ``measure_weight`` that follows it; the nominal mass is taken from the file
   (``target_volume_mL`` x ``density_g_per_mL``) unless overridden.
2. ``measurements.csv`` - every step of the run; the ``weight_g`` column of the
   ``measure_weight`` rows is used. The nominal mass must then come from
   ``--nominal`` or ``--volume``/``--density``.

The balance is tared before each dispense, so each weight is the net mass of
that dispense.

Usage:
    python -m src.gui.analyze_dispense_log logs/2026-09-08/zif8_..._120000
    python -m src.gui.analyze_dispense_log <run folder> --volume 5 --density 0.998
    python -m src.gui.analyze_dispense_log <run folder>/measurements.csv --nominal 4.99

The previous version of this script scraped weights out of the GUI's text log;
runs now always produce these CSVs (from the GUI and from the CLI alike), so
the log-parsing path is gone.
"""
import argparse
import csv
import os
import statistics
import sys

ACCURACY_CSV = "dispense_accuracy.csv"
MEASUREMENTS_CSV = "measurements.csv"


def _read_csv(path):
    # ExperimentLogger writes utf-8-sig so Excel opens the files cleanly.
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _to_float(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def read_accuracy_csv(path):
    """Return ``(weights, nominal_from_file)`` from a dispense_accuracy.csv."""
    weights, nominals = [], []
    for row in _read_csv(path):
        weight = _to_float(row.get("measured_weight_g"))
        if weight is None:
            continue
        weights.append(weight)
        expected = _to_float(row.get("expected_weight_g"))
        if expected is None:
            volume = _to_float(row.get("target_volume_mL"))
            density = _to_float(row.get("density_g_per_mL"))
            expected = volume * density if (volume and density) else None
        if expected is not None:
            nominals.append(expected)
    nominal = statistics.fmean(nominals) if nominals else None
    return weights, nominal


def read_measurements_csv(path):
    """Return the ``weight_g`` values of the measure_weight rows, in order."""
    weights = []
    for row in _read_csv(path):
        if row.get("status") not in (None, "", "ok"):
            continue
        weight = _to_float(row.get("weight_g"))
        if weight is not None:
            weights.append(weight)
    return weights


def load_weights(target):
    """Resolve a run folder or a CSV path to ``(weights, nominal, source)``."""
    if os.path.isdir(target):
        accuracy = os.path.join(target, ACCURACY_CSV)
        if os.path.exists(accuracy):
            weights, nominal = read_accuracy_csv(accuracy)
            if weights:
                return weights, nominal, accuracy
        measurements = os.path.join(target, MEASUREMENTS_CSV)
        if os.path.exists(measurements):
            return read_measurements_csv(measurements), None, measurements
        raise FileNotFoundError(
            f"Neither {ACCURACY_CSV} nor {MEASUREMENTS_CSV} found in {target}"
        )

    if os.path.basename(target) == ACCURACY_CSV:
        weights, nominal = read_accuracy_csv(target)
        return weights, nominal, target
    return read_measurements_csv(target), None, target


def summarize(values, nominal):
    n = len(values)
    mean = statistics.fmean(values)
    # Sample statistics (n-1); undefined for a single measurement.
    stdev = statistics.stdev(values) if n >= 2 else 0.0
    variance = statistics.variance(values) if n >= 2 else 0.0
    return {
        "n": n,
        "mean": mean,
        "median": statistics.median(values),
        "stdev": stdev,
        "variance": variance,
        "cv": (stdev / mean * 100) if mean else float("nan"),
        "min": min(values),
        "max": max(values),
        "range": max(values) - min(values),
        "nominal": nominal,
        "bias": mean - nominal,
        "bias_pct": (mean - nominal) / nominal * 100 if nominal else float("nan"),
    }


def format_report(values, source, s) -> str:
    line = "=" * 60
    out = [line, f"Dispensing accuracy report  (source: {source})", line, "",
           "[ measurements ]", f"{'#':>3}  {'mass (g)':>10}  {'vs nominal':>11}"]
    for i, v in enumerate(values, 1):
        out.append(f"{i:>3}  {v:>10.3f}  {v - s['nominal']:>+11.3f}")
    out += [
        "",
        "[ statistics ]",
        f"  n                 : {s['n']}",
        f"  mean              : {s['mean']:.4f} g",
        f"  median            : {s['median']:.4f} g",
        f"  std. deviation    : {s['stdev']:.4f} g   (sample, n-1)",
        f"  variance          : {s['variance']:.5f} g^2",
        f"  CV                : {s['cv']:.2f} %      <- repeatability (precision)",
        f"  min / max         : {s['min']:.3f} / {s['max']:.3f} g",
        f"  range             : {s['range']:.3f} g",
        "",
        "[ against the nominal mass ]",
        f"  nominal           : {s['nominal']:.4f} g",
        f"  bias              : {s['bias']:+.4f} g ({s['bias_pct']:+.2f} %)"
        f"  <- trueness (accuracy)",
        line,
    ]
    return "\n".join(out)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Precision/accuracy statistics for a dispensing run"
    )
    p.add_argument(
        "run",
        help=f"run folder (logs/<date>/<name>_<timestamp>/) or a "
             f"{ACCURACY_CSV} / {MEASUREMENTS_CSV} path",
    )
    p.add_argument("--nominal", type=float, default=None,
                   help="nominal dispensed mass in g (overrides --volume/--density "
                        "and the value stored in dispense_accuracy.csv)")
    p.add_argument("--volume", type=float, default=5.0,
                   help="nominal dispensed volume in mL (default 5.0)")
    p.add_argument("--density", type=float, default=0.998,
                   help="liquid density in g/mL (default 0.998 = water at ~22 C)")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        values, nominal_from_file, source = load_weights(args.run)
    except (FileNotFoundError, NotADirectoryError, OSError) as e:
        print(f"Could not read the run: {e}", file=sys.stderr)
        return 2

    if not values:
        print("No weight measurements found. Does the run contain measure_weight "
              "steps that followed a dispense?", file=sys.stderr)
        return 1

    if args.nominal is not None:
        nominal = args.nominal
    elif nominal_from_file is not None:
        nominal = nominal_from_file
    else:
        nominal = args.volume * args.density

    print(format_report(values, source, summarize(values, nominal)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
