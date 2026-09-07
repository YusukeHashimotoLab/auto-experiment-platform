"""DispenseAccuracyLogger: dispense/measure_weight の対応付けと誤差計算"""
import csv
import os

import pytest

from src.flow.accuracy_logger import DispenseAccuracyLogger


def test_dispense_weight_pairing(tmp_path):
    path = str(tmp_path / "acc.csv")
    logger = DispenseAccuracyLogger(path, density=1.0)
    logger.record_dispense(volume=2.0, speed=5, iteration=1, step_index=3)
    err = logger.record_weight(2.1)
    assert err == pytest.approx(0.1)
    logger.finalize()

    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["target_volume_mL"] == "2.0000"
    assert rows[0]["measured_weight_g"] == "2.1000"
    assert rows[0]["error_g"] == "+0.1000"
    assert rows[0]["iteration"] == "1"


def test_density_applied_to_expected_weight(tmp_path):
    path = str(tmp_path / "acc.csv")
    logger = DispenseAccuracyLogger(path, density=0.789)  # エタノール
    logger.record_dispense(volume=2.0)
    err = logger.record_weight(1.578)  # 2.0 * 0.789 = 1.578
    assert err == pytest.approx(0.0, abs=1e-9)
    logger.finalize()


def test_weight_without_pending_dispense_is_skipped(tmp_path):
    path = str(tmp_path / "acc.csv")
    logger = DispenseAccuracyLogger(path)
    assert logger.record_weight(5.0) is None
    logger.finalize()
    assert not os.path.exists(path)  # 1行も記録が無ければファイルを作らない


def test_pending_is_consumed_once(tmp_path):
    path = str(tmp_path / "acc.csv")
    logger = DispenseAccuracyLogger(path)
    logger.record_dispense(volume=1.0)
    assert logger.record_weight(1.0) is not None
    assert logger.record_weight(1.0) is None  # 2回目は対応する dispense が無い
    logger.finalize()
