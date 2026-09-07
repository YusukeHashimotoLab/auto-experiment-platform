"""
L1層: 共有デバイス管理クラス（SharedDevices）

このモジュールは複数のロボットアーム間で共有される
デバイス（カメラ、電子天秤など）を管理します。

設計思想:
- ロボットアーム（LabRobot）とは独立したライフサイクルで管理
- 複数のロボットから同じデバイスにアクセス可能
- robot_idに依存しない操作インターフェース
"""

import asyncio
import logging
from typing import Optional

# ロギング設定
logger = logging.getLogger(__name__)


class SharedDevices:
    """
    共有デバイス管理クラス

    カメラや電子天秤など、特定のロボットアームに属さない
    共有リソースを管理します。
    """

    def __init__(self,
                 use_scale: bool = False,
                 use_camera: bool = False,
                 **device_configs):
        """
        SharedDevicesを初期化

        Args:
            use_scale: 電子天秤（BCE8221）を使用するか
            use_camera: Webcamを使用するか
            **device_configs: デバイス固有の設定
                - scale_port: str (デフォルト: 'COM4') - BCE8221天秤のCOMポート
                - camera_index: int (デフォルト: 1) - Webcamのデバイスインデックス
        """
        # デバイス使用フラグ
        self.use_scale = use_scale
        self.use_camera = use_camera

        # デバイスインスタンス（初期化前はNone）
        self.scale = None
        self.camera = None

        # デバイス設定
        self.device_configs = device_configs

        # 待機時間設定
        self.wait_after_scale = device_configs.get('wait_after_scale', 2.0)

        # 初期化フラグ
        self._initialized = False

    async def initialize(self) -> bool:
        """
        共有デバイスを初期化

        Returns:
            bool: 初期化が成功したらTrue
        """
        try:
            logger.info("=== SharedDevices 初期化開始 ===")

            # Scale（電子天秤）の初期化
            if self.use_scale:
                if not await self._initialize_scale():
                    return False

            # Camera（カメラ）の初期化
            if self.use_camera:
                if not await self._initialize_camera():
                    return False

            self._initialized = True
            logger.info("=== SharedDevices 全デバイス初期化完了 ===\n")
            return True

        except Exception as e:
            logger.error(f"SharedDevices初期化エラー: {e}")
            return False

    async def _initialize_scale(self) -> bool:
        """BCE8221電子天秤を初期化"""
        try:
            logger.info("BCE8221電子天秤を初期化中...")
            from src.devices.scale.BCE8221 import SerialBalance

            scale_port = self.device_configs.get('scale_port', 'COM4')
            self.scale = SerialBalance(port=scale_port)

            # 接続テスト（重量を取得してみる）
            weight = self.scale.get_weight()
            if weight is None:
                logger.error("BCE8221電子天秤から重量を取得できませんでした")
                return False

            logger.info(f"✓ BCE8221電子天秤初期化完了: {weight:.3f}g")
            return True

        except Exception as e:
            logger.error(f"BCE8221電子天秤初期化エラー: {e}")
            return False

    async def _initialize_camera(self) -> bool:
        """Webcamを初期化"""
        try:
            logger.info("Webcamを初期化中...")
            from src.devices.webcam import WebcamController

            camera_index = self.device_configs.get('camera_index', 1)
            self.camera = WebcamController(camera_index=camera_index)

            # カメラ接続
            if not self.camera.connect():
                logger.error("Webcamの接続に失敗しました")
                return False

            logger.info("✓ Webcam初期化完了")
            return True

        except Exception as e:
            logger.error(f"Webcam初期化エラー: {e}")
            return False

    # ========================================
    # 電子天秤操作
    # ========================================

    async def measure_weight(self, stabilization_count: int = 3) -> float:
        """
        BCE8221で安定した重量測定を行う

        Args:
            stabilization_count: 測定回数（中央値を返す）

        Returns:
            float: 測定重量（g）

        Raises:
            RuntimeError: 電子天秤が初期化されていない場合
            ValueError: 有効な重量が取得できなかった場合
        """
        if not self.use_scale or self.scale is None:
            raise RuntimeError("BCE8221電子天秤が初期化されていません")

        try:
            weights = []
            for i in range(stabilization_count):
                weight = self.scale.get_weight()
                if weight is not None:
                    weights.append(weight)
                await asyncio.sleep(0.5)

            if not weights:
                raise ValueError("有効な重量データを取得できませんでした")

            # 中央値を返す（外れ値の影響を減らす）
            weights.sort()
            median_weight = weights[len(weights) // 2]

            logger.info(f"✓ 重量測定: {median_weight:.3f}g")
            await asyncio.sleep(self.wait_after_scale)
            return median_weight

        except Exception as e:
            logger.error(f"重量測定エラー: {e}")
            raise

    async def tare_scale(self, delay: float = 1.0):
        """
        BCE8221電子天秤を風袋引き（ゼロ点リセット）

        Args:
            delay: 風袋引き後の待機時間（秒）

        Raises:
            RuntimeError: 電子天秤が初期化されていない場合
        """
        if not self.use_scale or self.scale is None:
            raise RuntimeError("BCE8221電子天秤が初期化されていません")

        try:
            logger.info("BCE8221電子天秤を風袋引き中...")
            self.scale.tare()
            await asyncio.sleep(delay)
            logger.info("✓ 風袋引き完了")

        except Exception as e:
            logger.error(f"風袋引きエラー: {e}")
            raise

    # ========================================
    # カメラ操作
    # ========================================

    async def capture_and_save(self, file_path: Optional[str] = None) -> Optional[str]:
        """
        Webcamで画像をキャプチャして保存

        Args:
            file_path: 保存先のファイル名（省略時は自動生成）

        Returns:
            Optional[str]: 保存したファイルパス。失敗時はNone

        Raises:
            RuntimeError: カメラが初期化されていません
        """
        if not self.use_camera or self.camera is None:
            raise RuntimeError("カメラが初期化されていません")

        try:
            logger.info("Webcamで画像キャプチャ・保存中...")
            saved_path = self.camera.capture_and_save(file_path)

            if saved_path:
                logger.info(f"✓ 画像キャプチャ・保存完了: {saved_path}")
            else:
                logger.warning("画像の取得・保存に失敗しました")

            return saved_path

        except Exception as e:
            logger.error(f"画像キャプチャ・保存エラー: {e}")
            raise

    # ========================================
    # ライフサイクル管理
    # ========================================

    async def cleanup(self):
        """全共有デバイスを安全に切断"""
        logger.info("=== SharedDevices 切断開始 ===")

        try:
            if self.scale:
                self.scale.close()
                logger.info("✓ BCE8221電子天秤切断完了")
        except Exception as e:
            logger.error(f"BCE8221電子天秤切断エラー: {e}")

        try:
            if self.camera:
                self.camera.disconnect()
                logger.info("✓ Webcam切断完了")
        except Exception as e:
            logger.error(f"Webcam切断エラー: {e}")

        logger.info("=== SharedDevices 全デバイス切断完了 ===")

    async def __aenter__(self):
        """非同期コンテキストマネージャ: 入口"""
        if not await self.initialize():
            raise RuntimeError("SharedDevicesの初期化に失敗しました")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャ: 出口"""
        await self.cleanup()
