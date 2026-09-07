"""
可動域バリデータ

X, Y, Z座標とJoint1角度の可動域を検証します。
"""

import logging
from typing import Dict, Optional, List

from .base import PositionValidator
from .exceptions import WorkspaceViolationError, ViolationDetail

logger = logging.getLogger(__name__)


class WorkspaceValidator(PositionValidator):
    """
    直交座標系の可動域バリデータ

    X, Y, Z各軸の最小・最大値とJoint1角度の範囲を検証します。

    Args:
        x_min, x_max: X軸の可動範囲 (mm)
        y_min, y_max: Y軸の可動範囲 (mm)
        z_min, z_max: Z軸の可動範囲 (mm)
        joint1_min, joint1_max: Joint1の可動範囲 (度)

    使用例:
        validator = WorkspaceValidator(
            x_min=-300, x_max=300,
            y_min=-300, y_max=300,
            z_min=-130, z_max=150,
            joint1_min=-135, joint1_max=135
        )

        # 検証（可動域外なら例外）
        validator.validate_xyz(x=200, y=100, z=50)
        validator.validate_joint1(angle=45)
    """

    def __init__(
        self,
        x_min: float = -300,
        x_max: float = 300,
        y_min: float = -300,
        y_max: float = 300,
        z_min: float = -130,
        z_max: float = 150,
        joint1_min: float = -135,
        joint1_max: float = 135,
    ):
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.z_min = z_min
        self.z_max = z_max
        self.joint1_min = joint1_min
        self.joint1_max = joint1_max

        logger.debug(
            f"WorkspaceValidator初期化: "
            f"X=[{x_min}, {x_max}], Y=[{y_min}, {y_max}], "
            f"Z=[{z_min}, {z_max}], Joint1=[{joint1_min}, {joint1_max}]"
        )

    def validate_xyz(self, x: float, y: float, z: float) -> None:
        """
        XYZ座標の検証

        Args:
            x: X座標 (mm)
            y: Y座標 (mm)
            z: Z座標 (mm)

        Raises:
            WorkspaceViolationError: 可動域外の場合
        """
        violations: List[ViolationDetail] = []

        # X軸チェック
        if x < self.x_min or x > self.x_max:
            violations.append(
                ViolationDetail(
                    axis="X",
                    current_value=x,
                    min_value=self.x_min,
                    max_value=self.x_max,
                )
            )

        # Y軸チェック
        if y < self.y_min or y > self.y_max:
            violations.append(
                ViolationDetail(
                    axis="Y",
                    current_value=y,
                    min_value=self.y_min,
                    max_value=self.y_max,
                )
            )

        # Z軸チェック
        if z < self.z_min or z > self.z_max:
            violations.append(
                ViolationDetail(
                    axis="Z",
                    current_value=z,
                    min_value=self.z_min,
                    max_value=self.z_max,
                )
            )

        if violations:
            raise WorkspaceViolationError(
                message="XYZ座標が可動域外です",
                target_position={"x": x, "y": y, "z": z},
                violations=violations,
            )

        logger.debug(f"XYZ座標検証OK: ({x:.2f}, {y:.2f}, {z:.2f})")

    def validate_joint1(self, angle: float) -> None:
        """
        Joint1角度の検証

        Args:
            angle: Joint1角度 (度)

        Raises:
            WorkspaceViolationError: 可動域外の場合
        """
        if angle < self.joint1_min or angle > self.joint1_max:
            raise WorkspaceViolationError(
                message="Joint1角度が可動域外です",
                target_position={"joint1": angle},
                violations=[
                    ViolationDetail(
                        axis="Joint1",
                        current_value=angle,
                        min_value=self.joint1_min,
                        max_value=self.joint1_max,
                    )
                ],
            )

        logger.debug(f"Joint1角度検証OK: {angle:.2f}°")

    def validate_z_relative(self, current_z: float, delta_z: float) -> None:
        """
        相対Z移動の検証

        Args:
            current_z: 現在のZ座標 (mm)
            delta_z: 移動量 (mm、正=上昇、負=下降)

        Raises:
            WorkspaceViolationError: 移動後が可動域外の場合
        """
        target_z = current_z + delta_z

        if target_z < self.z_min or target_z > self.z_max:
            raise WorkspaceViolationError(
                message="Z軸移動後の位置が可動域外です",
                target_position={"current_z": current_z, "delta_z": delta_z, "target_z": target_z},
                violations=[
                    ViolationDetail(
                        axis="Z",
                        current_value=target_z,
                        min_value=self.z_min,
                        max_value=self.z_max,
                    )
                ],
            )

        logger.debug(f"Z相対移動検証OK: {current_z:.2f} + {delta_z:.2f} = {target_z:.2f}")

    def validate_joint1_relative(self, current_angle: float, delta_angle: float) -> None:
        """
        相対Joint1回転の検証

        Args:
            current_angle: 現在のJoint1角度 (度)
            delta_angle: 回転量 (度)

        Raises:
            WorkspaceViolationError: 回転後が可動域外の場合
        """
        target_angle = current_angle + delta_angle

        if target_angle < self.joint1_min or target_angle > self.joint1_max:
            raise WorkspaceViolationError(
                message="Joint1回転後の角度が可動域外です",
                target_position={
                    "current_angle": current_angle,
                    "delta_angle": delta_angle,
                    "target_angle": target_angle,
                },
                violations=[
                    ViolationDetail(
                        axis="Joint1",
                        current_value=target_angle,
                        min_value=self.joint1_min,
                        max_value=self.joint1_max,
                    )
                ],
            )

        logger.debug(
            f"Joint1相対回転検証OK: {current_angle:.2f}° + {delta_angle:.2f}° = {target_angle:.2f}°"
        )

    def get_limits(self) -> Dict[str, Dict[str, float]]:
        """現在の可動域制限を取得"""
        return {
            "x": {"min": self.x_min, "max": self.x_max},
            "y": {"min": self.y_min, "max": self.y_max},
            "z": {"min": self.z_min, "max": self.z_max},
            "joint1": {"min": self.joint1_min, "max": self.joint1_max},
        }

    def __repr__(self) -> str:
        return (
            f"WorkspaceValidator("
            f"X=[{self.x_min}, {self.x_max}], "
            f"Y=[{self.y_min}, {self.y_max}], "
            f"Z=[{self.z_min}, {self.z_max}], "
            f"Joint1=[{self.joint1_min}, {self.joint1_max}])"
        )
