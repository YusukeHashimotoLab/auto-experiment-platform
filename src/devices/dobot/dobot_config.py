"""
Dobot ロボットアーム設定ファイル

ロボットアームの動作パラメータを管理するための設定クラスです。
移動速度、加速度、その他の動作設定を定義します。
"""

import logging

logger = logging.getLogger(__name__)


class DobotConfig:
    """Dobotロボットアームの設定クラス"""
    
    # 移動速度設定（速度プリセット）
    SPEED_PRESETS = {
        "超低速": {
            "joint_velocity": [20, 20, 20, 20, 20, 20, 20, 20],
            "joint_acceleration": [20, 20, 20, 20, 20, 20, 20, 20],
            "linear_velocity": 20,
            "linear_acceleration": 20,
            "description": "非常にゆっくりとした安全な動作"
        },
        "低速": {
            "joint_velocity": [50, 50, 50, 50, 50, 50, 50, 50],
            "joint_acceleration": [50, 50, 50, 50, 50, 50, 50, 50],
            "linear_velocity": 50,
            "linear_acceleration": 50,
            "description": "ゆっくりとした安全な動作"
        },
        "中速": {
            "joint_velocity": [100, 100, 100, 100, 100, 100, 100, 100],
            "joint_acceleration": [100, 100, 100, 100, 100, 100, 100, 100],
            "linear_velocity": 100,
            "linear_acceleration": 100,
            "description": "標準的な動作速度"
        },
        "高速": {
            "joint_velocity": [200, 200, 200, 200, 200, 200, 200, 200],
            "joint_acceleration": [200, 200, 200, 200, 200, 200, 200, 200],
            "linear_velocity": 100,
            "linear_acceleration": 100,
            "description": "高速動作（デフォルト設定）"
        },
        "超高速": {
            "joint_velocity": [300, 300, 300, 300, 300, 300, 300, 300],
            "joint_acceleration": [300, 300, 300, 300, 300, 300, 300, 300],
            "linear_velocity": 150,
            "linear_acceleration": 150,
            "description": "最高速度での動作"
        }
    }
    
    # デフォルト設定
    DEFAULT_SPEED = "中速"  # 今後のデフォルト速度
    
    # ホーミング設定
    HOME_SETTINGS = {
        "home_x": 250,
        "home_y": 0, 
        "home_z": 50,
        "home_r": 0
    }
    
    # 通信設定
    CONNECTION_SETTINGS = {
        "default_port": "COM4",
        "baudrate": 115200,
        "timeout": 5
    }
    
    # 可動域（安全範囲）はここでは定義しない。
    # repo 直下 config.yaml の workspace セクションを単一ソースとし、
    # src/devices/safety/validators の WorkspaceValidator が動作前検証を行う。

    # 作業位置設定
    WORK_POSITIONS = {
        "初期位置": {"x": 200, "y": 0, "z": 100, "r": 0},
        "待機位置": {"x": 250, "y": 0, "z": 150, "r": 0},
        "作業位置A": {"x": 200, "y": 100, "z": 50, "r": 0},
        "作業位置B": {"x": 200, "y": -100, "z": 50, "r": 90},
        "退避位置": {"x": 300, "y": 0, "z": 200, "r": 0}
    }
    
    @classmethod
    def get_speed_preset(cls, speed_name: str = None):
        """
        指定された速度プリセットを取得する
        
        Args:
            speed_name (str): 速度設定名。Noneの場合はデフォルト速度を使用
            
        Returns:
            dict: 速度設定パラメータ
        """
        if speed_name is None:
            speed_name = cls.DEFAULT_SPEED
            
        if speed_name not in cls.SPEED_PRESETS:
            logger.warning(f"警告: 速度設定 '{speed_name}' が見つかりません。デフォルト '{cls.DEFAULT_SPEED}' を使用します。")
            speed_name = cls.DEFAULT_SPEED
            
        return cls.SPEED_PRESETS[speed_name]
    
    @classmethod
    def list_speed_presets(cls):
        """利用可能な速度プリセットを表示する"""
        logger.info("利用可能な速度設定:")
        for name, config in cls.SPEED_PRESETS.items():
            current = " (現在のデフォルト)" if name == cls.DEFAULT_SPEED else ""
            logger.info(f"  {name}: {config['description']}{current}")
    
    @classmethod
    def get_work_position(cls, position_name: str):
        """
        指定された作業位置を取得する
        
        Args:
            position_name (str): 作業位置名
            
        Returns:
            dict: 位置座標 (x, y, z, r)
        """
        if position_name not in cls.WORK_POSITIONS:
            logger.warning(f"警告: 作業位置 '{position_name}' が見つかりません。")
            return None
            
        return cls.WORK_POSITIONS[position_name]
    
    @classmethod
    def list_work_positions(cls):
        """利用可能な作業位置を表示する"""
        logger.info("定義済み作業位置:")
        for name, pos in cls.WORK_POSITIONS.items():
            logger.info(f"  {name}: X={pos['x']}, Y={pos['y']}, Z={pos['z']}, R={pos['r']}")


if __name__ == "__main__":
    # 設定ファイルのテスト
    print("=== Dobot Configuration Test ===")
    
    # 速度設定の表示
    DobotConfig.list_speed_presets()
    
    print(f"\nデフォルト速度設定: {DobotConfig.DEFAULT_SPEED}")
    default_config = DobotConfig.get_speed_preset()
    print(f"設定値: {default_config}")
    
    print("\n" + "-" * 40)
    
    # 作業位置の表示
    DobotConfig.list_work_positions()
    
    print("\n初期位置の取得:")
    init_pos = DobotConfig.get_work_position("初期位置")
    print(f"初期位置: {init_pos}")