"""
L1層: バリデータモジュール

動作前検証を行うバリデータを提供します。
拡張可能な設計により、新しい検証ロジックを容易に追加できます。

使用例:
    from src.devices.safety.validators import WorkspaceValidator, WorkspaceViolationError

    validator = WorkspaceValidator(
        x_min=-300, x_max=300,
        y_min=-300, y_max=300,
        z_min=-130, z_max=150,
        joint1_min=-135, joint1_max=135
    )
    validator.validate_xyz(x=200, y=100, z=50)  # 可動域内ならOK
    validator.validate_joint1(angle=45)  # 可動域内ならOK
"""

from .base import PositionValidator, ValidationResult
from .exceptions import (
    ValidationError,
    WorkspaceViolationError,
    ViolationDetail,
)
from .workspace import WorkspaceValidator


def default_workspace_validator(**overrides) -> WorkspaceValidator:
    """既定の安全可動域で ``WorkspaceValidator`` を生成するファクトリ。

    可動域の値はリポジトリ直下 config.yaml の ``workspace`` セクション
    （src.config 経由）を単一ソースとする。src.config を import できない
    単体利用時は :class:`WorkspaceValidator` の既定（config.example.yaml と
    同値）にフォールバックする。呼び出し側は ``overrides`` で個別に
    上書きできる。

    Args:
        **overrides: WorkspaceValidator のコンストラクタ引数の上書き
            （例: ``z_min=-100``）

    Returns:
        WorkspaceValidator: 可動域バリデータ
    """
    params = {}
    try:
        from src import config as lab_config
        params.update(lab_config.get_workspace())
    except ImportError:
        # リポジトリルートが sys.path に無い単体利用時はクラス既定値で動作
        pass
    params.update(overrides)
    return WorkspaceValidator(**params)


__all__ = [
    # 基底クラス
    "PositionValidator",
    "ValidationResult",
    # 例外
    "ValidationError",
    "WorkspaceViolationError",
    "ViolationDetail",
    # バリデータ
    "WorkspaceValidator",
    # ファクトリ
    "default_workspace_validator",
]
