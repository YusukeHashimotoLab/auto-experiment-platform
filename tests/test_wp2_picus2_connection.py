"""WP-2 item 1: Picus2 の接続失敗を黙って握りつぶさないこと。

serial / bleak は実環境にしか無いので sys.modules へスタブを入れてから import する。
"""
import asyncio
import sys
import types

import pytest


def _install_stubs():
    """serial / bleak のスタブを sys.modules に入れる（既存があれば温存）。"""
    if "serial" not in sys.modules:
        serial_stub = types.ModuleType("serial")

        class _Serial:  # pragma: no cover - 既定では使わない
            def __init__(self, *a, **kw):
                self.is_open = True

            def close(self):
                self.is_open = False

        serial_stub.Serial = _Serial
        serial_stub.PARITY_ODD = "O"
        serial_stub.PARITY_NONE = "N"
        serial_stub.STOPBITS_ONE = 1
        serial_stub.EIGHTBITS = 8
        serial_stub.SEVENBITS = 7
        serial_stub.PARITY_EVEN = "E"
        serial_stub.STOPBITS_TWO = 2
        serial_stub.SerialException = type("SerialException", (Exception,), {})
        # 参照されていない定数もダミーで返す（pyserial 依存の広い import を通すため）
        serial_stub.__getattr__ = lambda name: 0 if name.isupper() else None
        tools = types.ModuleType("serial.tools")
        list_ports = types.ModuleType("serial.tools.list_ports")
        list_ports.comports = lambda: []
        tools.list_ports = list_ports
        serial_stub.tools = tools
        sys.modules["serial"] = serial_stub
        sys.modules["serial.tools"] = tools
        sys.modules["serial.tools.list_ports"] = list_ports

    if "bleak" not in sys.modules:
        bleak_stub = types.ModuleType("bleak")

        class _BleakClient:  # pragma: no cover
            def __init__(self, address):
                self.address = address
                self.is_connected = False

        bleak_stub.BleakClient = _BleakClient
        sys.modules["bleak"] = bleak_stub


_install_stubs()

from src.devices.picus2.picus2_controller import (  # noqa: E402
    ConnectionType,
    Picus2Controller,
)


class _FailingSerial:
    def __init__(self, *a, **kw):
        raise OSError("could not open port COM4")


class _ClosedSerial:
    def __init__(self, *a, **kw):
        self.is_open = False


class _OpenSerial:
    def __init__(self, *a, **kw):
        self.is_open = True
        self.written = []

    def flush(self):
        pass

    def write(self, data):
        self.written.append(data)

    def close(self):
        self.is_open = False


def test_connect_usb_raises_connection_error_with_port_and_cause(monkeypatch):
    monkeypatch.setattr(sys.modules["serial"], "Serial", _FailingSerial, raising=False)
    picus = Picus2Controller("COM4")
    with pytest.raises(ConnectionError) as exc:
        asyncio.run(picus.connect())
    assert "COM4" in str(exc.value)
    assert "could not open port" in str(exc.value)


def test_connect_usb_raises_when_port_opens_but_is_closed(monkeypatch):
    monkeypatch.setattr(sys.modules["serial"], "Serial", _ClosedSerial, raising=False)
    picus = Picus2Controller("COM7")
    with pytest.raises(ConnectionError):
        asyncio.run(picus.connect())


def test_connect_usb_returns_true_on_success(monkeypatch):
    monkeypatch.setattr(sys.modules["serial"], "Serial", _OpenSerial, raising=False)
    picus = Picus2Controller("COM4")
    assert asyncio.run(picus.connect()) is True
    assert picus.is_connected is True


def test_connect_bluetooth_raises_connection_error(monkeypatch):
    class _FailingClient:
        def __init__(self, address):
            self.address = address
            self.is_connected = False

        async def connect(self):
            raise OSError("BLE device not found")

    monkeypatch.setattr(sys.modules["bleak"], "BleakClient", _FailingClient, raising=False)
    picus = Picus2Controller("AA:BB:CC:DD:EE:FF", connection_type=ConnectionType.BLUETOOTH)
    with pytest.raises(ConnectionError) as exc:
        asyncio.run(picus.connect())
    assert "AA:BB:CC:DD:EE:FF" in str(exc.value)


@pytest.mark.parametrize(
    "call",
    [
        lambda p: p.set_motor_mode(True),
        lambda p: p.aspirate(1.0, speed=5),
        lambda p: p.dispense(1.0, speed=5),
        lambda p: p.blow_out(),
    ],
)
def test_operations_raise_when_not_connected(call):
    """未接続のまま操作要求されたら黙って no-op せず ConnectionError を投げる。"""
    picus = Picus2Controller("COM4")
    picus.motor_mode = True  # モーターモード例外ではなく接続例外であることを確認
    with pytest.raises(ConnectionError):
        asyncio.run(call(picus))


def test_initialize_picus2_treats_falsy_connect_as_failure(monkeypatch):
    """connect() が False/None を返す実装でも成功扱いにしない。"""
    from src.devices.safety.lab_robot import LabRobot

    class _SilentPicus:
        def __init__(self, address, connection_type=None):
            self.address = address
            self.motor_mode_calls = []

        async def connect(self):
            return False

        async def set_motor_mode(self, mode):
            self.motor_mode_calls.append(mode)

    import src.devices.picus2 as picus2_pkg

    monkeypatch.setattr(picus2_pkg, "Picus2Controller", _SilentPicus, raising=False)

    robot = LabRobot(use_dobot=False, use_picus2=True, use_ika=False)
    robot.picus2_max_retries = 1
    robot.picus2_retry_delays = [0]

    assert asyncio.run(robot._initialize_picus2()) is False
