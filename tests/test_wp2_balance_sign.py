"""WP-2 item 2: BCE8221 のプリントアウトで符号が失われないこと。"""
import sys
import types

import pytest

from tests.test_wp2_picus2_connection import _install_stubs  # noqa: F401  (serial スタブ)

_install_stubs()

from src.devices.scale.BCE8221 import SerialBalance  # noqa: E402


def _balance():
    """シリアルポートを開かずに SerialBalance を生成する。"""
    return object.__new__(SerialBalance)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("-     0.03 g", -0.03),          # 符号とスペースが数字と離れている（本件の再現ケース）
        ("+    12.34 g", 12.34),
        ("12.34 g", 12.34),
        ("N  +  0.00 g", 0.0),            # 不安定マーカー付き
        ("N  -  1.25 g", -1.25),
        ("      0.00 g", 0.0),
        ("-0.03 g", -0.03),
        ("G     5.00 g", 5.0),            # Gross マーカー
    ],
)
def test_extract_number_preserves_sign(raw, expected):
    assert _balance().extract_number(raw) == pytest.approx(expected)


@pytest.mark.parametrize("raw", ["", "   g", "Error", "----"])
def test_extract_number_returns_none_when_no_number(raw):
    assert _balance().extract_number(raw) is None


def test_get_weight_returns_none_without_crashing():
    class _Ser:
        def write(self, data):
            pass

        def readline(self):
            return b"Error\r\n"

    bal = _balance()
    bal.ser = _Ser()
    assert bal.get_weight() is None


def test_get_weight_parses_negative():
    class _Ser:
        def write(self, data):
            pass

        def readline(self):
            return b"-     0.03 g\r\n"

    bal = _balance()
    bal.ser = _Ser()
    assert bal.get_weight() == pytest.approx(-0.03)


def test_measure_weight_handles_negative_and_none():
    """SharedDevices.measure_weight が負値・None 混在でも中央値を返す。"""
    import asyncio

    from src.devices.safety.shared_devices import SharedDevices

    class _Scale:
        def __init__(self):
            self.values = [-0.03, None, -0.05, -0.04]
            self.i = 0

        def get_weight(self):
            v = self.values[self.i % len(self.values)]
            self.i += 1
            return v

    dev = object.__new__(SharedDevices)
    dev.use_scale = True
    dev.scale = _Scale()
    dev.wait_after_scale = 0

    result = asyncio.run(dev.measure_weight(stabilization_count=4))
    assert result < 0
    assert result == pytest.approx(-0.04)
