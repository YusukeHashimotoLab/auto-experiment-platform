"""WorkspaceValidator: 可動域検証と config 配線"""
import pytest

from src.devices.safety.validators import (
    WorkspaceValidator,
    WorkspaceViolationError,
    default_workspace_validator,
)


def test_xyz_within_range_passes():
    v = default_workspace_validator()
    v.validate_xyz(x=200, y=100, z=50)  # 例外が出なければOK


def test_z_below_range_raises():
    v = default_workspace_validator()
    with pytest.raises(WorkspaceViolationError):
        v.validate_xyz(x=200, y=0, z=-200)


def test_z_above_range_raises():
    v = default_workspace_validator()
    with pytest.raises(WorkspaceViolationError):
        v.validate_xyz(x=200, y=0, z=200)


def test_joint1_within_range_passes():
    v = default_workspace_validator()
    v.validate_joint1(45)


def test_joint1_out_of_range_raises():
    v = default_workspace_validator()
    with pytest.raises(WorkspaceViolationError):
        v.validate_joint1(-180)  # joint1_min=-135 より小さい


def test_factory_uses_config_workspace():
    """config.yaml の workspace セクションが配線されている"""
    from src import config as lab_config

    v = default_workspace_validator()
    ws = lab_config.get_workspace()
    assert v.z_min == ws["z_min"]
    assert v.z_max == ws["z_max"]
    assert v.joint1_min == ws["joint1_min"]
    assert v.joint1_max == ws["joint1_max"]


def test_factory_overrides_beat_config():
    v = default_workspace_validator(z_min=-77.0)
    assert v.z_min == -77.0
    assert v.z_max == 150.0  # 他は config のまま


def test_class_defaults_match_config():
    """単体利用時のクラス既定値が config.yaml とドリフトしていない"""
    from src import config as lab_config

    bare = WorkspaceValidator()
    ws = lab_config.get_workspace()
    assert bare.z_min == ws["z_min"]
    assert bare.z_max == ws["z_max"]
    assert bare.joint1_min == ws["joint1_min"]
    assert bare.joint1_max == ws["joint1_max"]
