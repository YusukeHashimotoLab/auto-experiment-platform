"""
L1層: 安全ラッパ層

L0層のデバイスドライバを安全にラップし、
実験ワークフローで使いやすいインターフェースを提供します。

- LabRobot: ロボットアーム毎のデバイス管理（Dobot, Picus2等）
- SharedDevices: 共有デバイス管理（カメラ, 電子天秤等）
"""

from .lab_robot import LabRobot
from .shared_devices import SharedDevices

__all__ = ['LabRobot', 'SharedDevices']

__version__ = '1.0.0'
