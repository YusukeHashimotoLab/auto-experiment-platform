"""
バリデータ基底クラス

拡張可能なバリデータインターフェースを定義します。
新しいバリデータを追加する場合は、PositionValidatorを継承してください。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class ValidationResult:
    """バリデーション結果"""

    is_valid: bool
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class PositionValidator(ABC):
    """
    位置バリデータの抽象基底クラス

    新しいバリデータを追加する場合は、このクラスを継承し、
    validate_xyz() と validate_joint1() を実装してください。

    使用例:
        class MyCustomValidator(PositionValidator):
            def validate_xyz(self, x, y, z):
                # カスタム検証ロジック
                pass

            def validate_joint1(self, angle):
                # カスタム検証ロジック
                pass
    """

    @abstractmethod
    def validate_xyz(
        self,
        x: float,
        y: float,
        z: float,
    ) -> None:
        """
        XYZ座標の検証

        Args:
            x: X座標 (mm)
            y: Y座標 (mm)
            z: Z座標 (mm)

        Raises:
            WorkspaceViolationError: 可動域外の場合
        """
        pass

    @abstractmethod
    def validate_joint1(self, angle: float) -> None:
        """
        Joint1角度の検証

        Args:
            angle: Joint1角度 (度)

        Raises:
            WorkspaceViolationError: 可動域外の場合
        """
        pass

    @abstractmethod
    def validate_z_relative(self, current_z: float, delta_z: float) -> None:
        """
        相対Z移動の検証

        Args:
            current_z: 現在のZ座標 (mm)
            delta_z: 移動量 (mm、正=上昇、負=下降)

        Raises:
            WorkspaceViolationError: 移動後が可動域外の場合
        """
        pass

    def get_limits(self) -> Dict[str, Dict[str, float]]:
        """
        現在の可動域制限を取得

        Returns:
            dict: 各軸の制限値 {"x": {"min": ..., "max": ...}, ...}
        """
        return {}
