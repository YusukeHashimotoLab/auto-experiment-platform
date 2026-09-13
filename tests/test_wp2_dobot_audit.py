"""Dobot driver: Dobot ドライバの動作系メソッドが未接続時に黙って no-op しないこと。"""
import inspect

import pytest

from src.devices.dobot.pydobot_controller import PyDobotController

MOTION_METHODS = [
    "move_XYZ_abs",
    "move_Z",
    "move_angle",
    "move_XY",
    "move_slider",
    "move_conveyer",
    "get_current_position",
    "set_gripper",
    "set_suction_cup",
]


def _disconnected():
    ctrl = object.__new__(PyDobotController)
    ctrl.port_name = "TEST"
    ctrl.device = None
    ctrl._connected = False
    ctrl.verbose = False
    return ctrl


@pytest.mark.parametrize("name", MOTION_METHODS)
def test_motion_methods_guard_with_require_device(name):
    src = inspect.getsource(getattr(PyDobotController, name))
    assert "_require_device()" in src, f"{name} が _require_device() を呼んでいない"


@pytest.mark.parametrize(
    "name,args",
    [
        ("move_XYZ_abs", (200, 0, 100)),
        ("move_Z", (10,)),
        ("move_angle", (90,)),
        ("move_XY", (10, 10)),
        ("get_current_position", ()),
        ("set_gripper", (True, True)),
        ("set_suction_cup", (True, True)),
        ("move_slider", (10,)),
        ("move_conveyer", (0, 10, 1)),
        ("pickup", (10, 10, -10)),
        ("place", (10, 10, -10)),
        ("move_to_initial_pos", ()),
    ],
)
def test_disconnected_operations_raise(name, args):
    ctrl = _disconnected()
    with pytest.raises(ConnectionError):
        getattr(ctrl, name)(*args)


def test_force_stop_exists_and_reports_failure_when_disconnected():
    assert callable(getattr(PyDobotController, "force_stop", None))
    assert _disconnected().force_stop() is False
