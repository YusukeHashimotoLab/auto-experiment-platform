"""CsvRecorder: 逐次追記・遅延生成・close セマンティクス"""
import csv
import os
import sys

import pytest

# ダッシュボードモジュールを直接ロードする（cv2 / fastapi が必要）
cv2 = pytest.importorskip("cv2")
pytest.importorskip("fastapi")

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "src", "monitoring", "dashboard",
    ),
)
from launch_sensor_dashboard import CSV_FIELDS, CsvRecorder  # noqa: E402


def make_row(**overrides):
    row = {k: 1 for k in CSV_FIELDS}
    row.update(overrides)
    return row


def test_file_is_created_lazily(tmp_path):
    path = str(tmp_path / "a.csv")
    rec = CsvRecorder(path, CSV_FIELDS)
    assert not os.path.exists(path)  # 行が来るまでファイルを作らない
    rec.write_row(make_row())
    assert os.path.exists(path)


def test_rows_are_flushed_during_recording(tmp_path, monkeypatch):
    """録画中（close 前）にディスクへ反映される — 停止時一括方式との本質的差分"""
    monkeypatch.setattr(CsvRecorder, "FLUSH_INTERVAL", 0.0)
    path = str(tmp_path / "a.csv")
    rec = CsvRecorder(path, CSV_FIELDS)
    for _ in range(3):
        rec.write_row(make_row())
    with open(path, newline="", encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) == 3
    rec.close()


def test_close_returns_path_when_rows_written(tmp_path):
    path = str(tmp_path / "a.csv")
    rec = CsvRecorder(path, CSV_FIELDS)
    rec.write_row(make_row())
    assert rec.close() == path


def test_close_returns_none_when_empty(tmp_path):
    path = str(tmp_path / "a.csv")
    rec = CsvRecorder(path, CSV_FIELDS)
    assert rec.close() is None
    assert not os.path.exists(path)


def test_write_after_close_is_ignored(tmp_path):
    """停止処理と録画スレッド最終tickの競合安全"""
    path = str(tmp_path / "a.csv")
    rec = CsvRecorder(path, CSV_FIELDS)
    rec.write_row(make_row())
    rec.close()
    rec.write_row(make_row())
    with open(path, newline="", encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) == 1


def test_write_failure_does_not_raise(tmp_path):
    """ディスクエラーで録画スレッドを巻き込まない"""
    rec = CsvRecorder(str(tmp_path / "no_dir_\x00bad" / "x.csv"), CSV_FIELDS)
    rec.write_row(make_row())  # open 失敗 → 例外を出さず _failed
    rec.write_row(make_row())  # 以降は静かにスキップ
    assert rec.close() is None
