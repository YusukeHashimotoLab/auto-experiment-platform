"""
バリデーション例外クラス

動作前検証で発生するエラーを定義します。
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List


class ValidationError(Exception):
    """バリデーションエラーの基底クラス"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


@dataclass
class ViolationDetail:
    """違反の詳細情報"""

    axis: str  # 違反した軸/パラメータ名 ("x", "y", "z", "joint1")
    current_value: float  # 現在/要求値
    min_value: float  # 許容最小値
    max_value: float  # 許容最大値

    @property
    def violation_amount(self) -> float:
        """範囲外の量を計算（正=上限超過、負=下限未満）"""
        if self.current_value > self.max_value:
            return self.current_value - self.max_value
        elif self.current_value < self.min_value:
            return self.current_value - self.min_value
        return 0.0

    def __str__(self) -> str:
        if self.current_value > self.max_value:
            return f"{self.axis}: {self.current_value:.2f} > 最大値 {self.max_value:.2f} (超過: {self.violation_amount:.2f})"
        elif self.current_value < self.min_value:
            return f"{self.axis}: {self.current_value:.2f} < 最小値 {self.min_value:.2f} (不足: {abs(self.violation_amount):.2f})"
        return f"{self.axis}: {self.current_value:.2f} (範囲内)"


class WorkspaceViolationError(ValidationError):
    """
    可動域違反エラー

    ロボットアームが可動域外に移動しようとした場合に発生します。

    Attributes:
        target_position: 要求された目標位置 dict (x, y, z, joint1など)
        violations: 違反の詳細リスト
    """

    def __init__(
        self,
        message: str,
        target_position: Dict[str, float],
        violations: List[ViolationDetail],
    ):
        details = {
            "target_position": target_position,
            "violations": [str(v) for v in violations],
        }
        super().__init__(message, details)
        self.target_position = target_position
        self.violations = violations

    def __str__(self) -> str:
        pos_str = ", ".join(f"{k}={v:.2f}" for k, v in self.target_position.items())
        violation_strs = "\n  - ".join(str(v) for v in self.violations)
        return (
            f"{self.message}\n"
            f"目標位置: ({pos_str})\n"
            f"違反内容:\n  - {violation_strs}"
        )
