"""src/gui/analyze_dispense_log.py: statistics from a run folder's CSVs."""
import csv

import pytest

from src.gui import analyze_dispense_log as analyze

ACCURACY_FIELDS = [
    "timestamp", "iteration", "dispense_step", "target_volume_mL", "speed",
    "density_g_per_mL", "expected_weight_g", "measured_weight_g",
    "error_g", "error_pct",
]
MEASUREMENT_FIELDS = [
    "timestamp", "elapsed_s", "step_index", "total_steps", "iteration", "action",
    "robot_id", "status", "duration_s", "weight_g", "image_path", "error",
]


def write_csv(path, fields, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def make_run(tmp_path, weights=(4.98, 5.02, 5.00), accuracy=True):
    run = tmp_path / "run"
    run.mkdir(exist_ok=True)
    if accuracy:
        write_csv(run / analyze.ACCURACY_CSV, ACCURACY_FIELDS, [
            {"target_volume_mL": "5.0000", "density_g_per_mL": "1.0000",
             "expected_weight_g": "5.0000", "measured_weight_g": f"{w:.4f}",
             "dispense_step": i}
            for i, w in enumerate(weights, 1)
        ])
    write_csv(run / analyze.MEASUREMENTS_CSV, MEASUREMENT_FIELDS, [
        {"step_index": 1, "action": "tare_scale", "status": "ok", "weight_g": ""},
        *[{"step_index": i + 1, "action": "measure_weight", "status": "ok",
           "weight_g": f"{w:.3f}"} for i, w in enumerate(weights)],
    ])
    return run


def test_prefers_the_dispense_accuracy_csv(tmp_path):
    run = make_run(tmp_path)
    weights, nominal, source = analyze.load_weights(str(run))
    assert weights == [4.98, 5.02, 5.00]
    assert nominal == pytest.approx(5.0)
    assert source.endswith(analyze.ACCURACY_CSV)


def test_falls_back_to_measurements_csv(tmp_path):
    """A run without dispense steps still yields the weighed masses."""
    run = make_run(tmp_path, accuracy=False)
    weights, nominal, source = analyze.load_weights(str(run))
    assert weights == [4.98, 5.02, 5.00]
    assert nominal is None
    assert source.endswith(analyze.MEASUREMENTS_CSV)


def test_missing_run_folder_is_reported(tmp_path):
    with pytest.raises(FileNotFoundError):
        analyze.load_weights(str(tmp_path / "empty"))
    (tmp_path / "empty").mkdir()
    with pytest.raises(FileNotFoundError):
        analyze.load_weights(str(tmp_path / "empty"))


def test_summary_statistics():
    s = analyze.summarize([4.98, 5.02, 5.00], nominal=5.0)
    assert s["n"] == 3
    assert s["mean"] == pytest.approx(5.0)
    assert s["stdev"] == pytest.approx(0.02)
    assert s["cv"] == pytest.approx(0.4)
    assert s["bias"] == pytest.approx(0.0, abs=1e-9)
    assert s["range"] == pytest.approx(0.04)


def test_cli_reports_precision_and_trueness(tmp_path, capsys):
    run = make_run(tmp_path, weights=(4.90, 4.90))
    assert analyze.main([str(run), "--nominal", "5.0"]) == 0
    out = capsys.readouterr().out
    assert "CV" in out and "bias" in out
    assert "-0.1000 g" in out          # 4.90 - 5.00
    assert "n                 : 2" in out


def test_cli_reports_when_there_is_nothing_to_analyse(tmp_path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    write_csv(run / analyze.MEASUREMENTS_CSV, MEASUREMENT_FIELDS,
              [{"step_index": 1, "action": "go_home", "status": "ok", "weight_g": ""}])
    assert analyze.main([str(run)]) == 1
    assert "No weight measurements" in capsys.readouterr().err
