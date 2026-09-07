"""WP-2 item 3: LabRobot が呼ぶ IKA の API が実際に存在すること／import が Tk を要求しないこと。"""
import asyncio
import sys

import pytest

from tests.test_wp2_picus2_connection import _install_stubs  # serial スタブ

_install_stubs()

from src.devices.ika import IKAController  # noqa: E402


def test_ika_controller_exposes_connect_and_disconnect():
    for name in ("connect", "disconnect", "close", "is_connected"):
        assert callable(getattr(IKAController, name, None)), f"IKAController.{name} が無い"


def test_import_does_not_pull_matplotlib_backend(monkeypatch):
    """モジュール import 時に matplotlib.use()（Tk）を呼ばないこと。"""
    import importlib

    calls = []

    import matplotlib

    monkeypatch.setattr(matplotlib, "use", lambda *a, **kw: calls.append(a))
    sys.modules.pop("src.devices.ika.ika_controller", None)
    sys.modules.pop("src.devices.ika", None)
    importlib.import_module("src.devices.ika.ika_controller")
    assert calls == [], f"import 時に matplotlib.use が呼ばれた: {calls}"


class _FakeIKA:
    """実 IKAController に存在するメソッドしか許さないスタブ。"""

    def __init__(self, port=None, **kw):
        self.port = port
        self.opened = False
        self.calls = []

    def __getattr__(self, name):
        if not hasattr(IKAController, name):
            raise AttributeError(
                f"LabRobot が IKAController に存在しない属性 {name!r} を呼び出した"
            )
        raise AttributeError(name)

    def connect(self):
        self.opened = True
        self.calls.append("connect")
        return True

    def disconnect(self):
        self.opened = False
        self.calls.append("disconnect")
        return True

    def is_connected(self):
        return self.opened

    def close(self):
        self.opened = False


def test_lab_robot_initialize_use_ika_does_not_raise_attribute_error(monkeypatch):
    from src.devices.safety.lab_robot import LabRobot
    import src.devices.ika as ika_pkg

    monkeypatch.setattr(ika_pkg, "IKAController", _FakeIKA, raising=False)

    robot = LabRobot(use_dobot=False, use_picus2=False, use_ika=True)
    assert asyncio.run(robot.initialize()) is True
    assert robot.ika.calls == ["connect"]

    asyncio.run(robot.cleanup())
    assert robot.ika.calls == ["connect", "disconnect"]
