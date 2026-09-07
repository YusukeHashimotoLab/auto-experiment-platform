#!/usr/bin/env python3
"""
ウェブカメラ制御クラス

OpenCVを使用してウェブカメラから画像を取得し、
実験記録用の画像を保存する機能を提供します。

作成者: Claude Code
作成日: 2025年6月23日
"""

import cv2
import numpy as np
import time
import os
import platform
from datetime import datetime
from typing import Optional, Tuple, Union
import logging

# ロギング設定
logger = logging.getLogger(__name__)


class WebcamController:
    """
    ウェブカメラを制御して画像取得を行うクラス
    
    OpenCVを使用してUSB接続されたウェブカメラから
    静止画の取得、保存、プレビュー表示を行います。
    """
    
    def __init__(self, camera_index: int = 1, resolution: Optional[Tuple[int, int]] = None):
        """
        ウェブカメラコントローラーを初期化

        Args:
            camera_index: カメラデバイスのインデックス（デフォルト: 1）
            resolution: 解像度のタプル (width, height)。Noneの場合はデフォルト解像度
        """
        self.camera_index = camera_index
        self.resolution = resolution or (1280, 720)  # デフォルトHD解像度
        self.camera = None
        self.is_connected = False
        
        # 画像保存設定
        self.save_directory = "captured_images"
        self._ensure_save_directory()
        
    def _ensure_save_directory(self):
        """画像保存ディレクトリを確認・作成"""
        if not os.path.exists(self.save_directory):
            os.makedirs(self.save_directory)
            logger.info(f"画像保存ディレクトリを作成: {self.save_directory}")
            
    def connect(self) -> bool:
        """
        ウェブカメラに接続

        Returns:
            接続成功時True、失敗時False
        """
        try:
            # OSに応じた最適なバックエンドを選択
            os_name = platform.system()
            if os_name == "Windows":
                backend = cv2.CAP_MSMF  # Media Foundation（高速）
            elif os_name == "Linux":
                backend = cv2.CAP_V4L2  # Video4Linux2
            elif os_name == "Darwin":  # macOS
                backend = cv2.CAP_AVFOUNDATION
            else:
                backend = cv2.CAP_ANY  # フォールバック

            # カメラオブジェクトを作成（バックエンド指定）
            self.camera = cv2.VideoCapture(self.camera_index, backend)

            # バッファサイズを最小化（応答性向上）
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not self.camera.isOpened():
                logger.error(f"カメラインデックス {self.camera_index} を開けません")
                return False
                
            # 解像度を設定
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            
            # 実際の解像度を取得
            actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            logger.info(f"ウェブカメラ接続成功 - インデックス: {self.camera_index}")
            logger.info(f"解像度: {actual_width}x{actual_height}")
            
            self.is_connected = True
            return True
            
        except Exception as e:
            logger.error(f"ウェブカメラ接続エラー: {e}")
            self.is_connected = False
            return False
            
    def disconnect(self):
        """ウェブカメラから切断"""
        if self.camera is not None:
            self.camera.release()
            cv2.destroyAllWindows()
            self.is_connected = False
            logger.info("ウェブカメラから切断しました")
            
    def capture_image(self) -> Optional[np.ndarray]:
        """
        画像を1枚キャプチャ
        
        Returns:
            キャプチャした画像（numpy配列）。失敗時はNone
        """
        if not self.is_connected:
            logger.error("カメラが接続されていません")
            return None
            
        try:
            # 数フレーム読み捨て（カメラの安定化）
            for _ in range(5):
                self.camera.read()
                
            # 画像キャプチャ
            ret, frame = self.camera.read()
            
            if ret:
                logger.info("画像キャプチャ成功")
                return frame
            else:
                logger.error("画像キャプチャ失敗")
                return None
                
        except Exception as e:
            logger.error(f"画像キャプチャエラー: {e}")
            return None
            
    def save_image(self, image: np.ndarray, filename: Optional[str] = None) -> Optional[str]:
        """
        画像をファイルに保存

        Args:
            image: 保存する画像（numpy配列）
            filename: ファイル名またはファイルパス。Noneの場合はタイムスタンプで自動生成

        Returns:
            保存したファイルのパス。失敗時はNone
        """
        try:
            if filename is None or filename == "":
                # 日付ディレクトリとタイムスタンプベースのファイル名生成
                now = datetime.now()
                date_dir = now.strftime("%Y%m%d")
                timestamp = now.strftime("%Y%m%d_%H%M%S")
                filename = f"capture_{timestamp}.jpg"
                filepath = os.path.join(self.save_directory, date_dir, filename)
            elif os.path.isabs(filename):
                # 絶対パスの場合はそのまま使用
                filepath = filename
            elif filename.startswith(self.save_directory):
                # 既にsave_directoryで始まる場合はそのまま使用（二重パス防止）
                filepath = filename
            else:
                # 相対パスの場合はsave_directoryと結合
                filepath = os.path.join(self.save_directory, filename)

            # 保存先ディレクトリが存在しない場合は作成
            parent_dir = os.path.dirname(filepath)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
                logger.info(f"ディレクトリを作成: {parent_dir}")

            # 画像保存
            success = cv2.imwrite(filepath, image)

            if success:
                logger.info(f"画像保存成功: {filepath}")
                return filepath
            else:
                logger.error(f"画像保存失敗: {filepath}")
                return None

        except Exception as e:
            logger.error(f"画像保存エラー: {e}")
            return None
            
    def capture_and_save(self, filename: Optional[str] = None) -> Optional[str]:
        """
        画像をキャプチャして保存
        
        Args:
            filename: 保存ファイル名。Noneの場合は自動生成
            
        Returns:
            保存したファイルのパス。失敗時はNone
        """
        image = self.capture_image()
        if image is not None:
            return self.save_image(image, filename)
        return None
        
    def show_preview(self, duration: int = 0):
        """
        カメラのプレビューを表示
        
        Args:
            duration: 表示時間（秒）。0の場合はキー入力まで表示
        """
        if not self.is_connected:
            logger.error("カメラが接続されていません")
            return
            
        try:
            logger.info("プレビュー開始（'q'キーで終了）")
            start_time = time.time()
            
            while True:
                ret, frame = self.camera.read()
                if not ret:
                    break
                    
                # 画像表示
                cv2.imshow('Webcam Preview', frame)
                
                # キー入力チェック
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
                # 時間制限チェック
                if duration > 0 and (time.time() - start_time) > duration:
                    break
                    
            cv2.destroyWindow('Webcam Preview')
            logger.info("プレビュー終了")
            
        except Exception as e:
            logger.error(f"プレビューエラー: {e}")
            
    def get_camera_info(self) -> dict:
        """
        カメラ情報を取得
        
        Returns:
            カメラ情報の辞書
        """
        if not self.is_connected:
            return {"error": "カメラが接続されていません"}
            
        try:
            info = {
                "index": self.camera_index,
                "width": int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "fps": int(self.camera.get(cv2.CAP_PROP_FPS)),
                "backend": self.camera.getBackendName()
            }
            return info
            
        except Exception as e:
            return {"error": str(e)}
            
    def __enter__(self):
        """コンテキストマネージャー開始"""
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー終了"""
        self.disconnect()


# 実験統合用の便利関数
def capture_experiment_image(step_name: str, camera_index: int = 1) -> Optional[str]:
    """
    実験ステップの画像を撮影
    
    Args:
        step_name: 実験ステップ名
        camera_index: カメラインデックス
        
    Returns:
        保存したファイルパス
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"experiment_{step_name}_{timestamp}.jpg"
    
    with WebcamController(camera_index) as webcam:
        return webcam.capture_and_save(filename)


# テスト・デモ用
if __name__ == "__main__":
    import sys
    
    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=== ウェブカメラコントローラー テスト ===")
    
    # カメラインデックスを引数から取得（デフォルト: 1）
    camera_index = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    
    # ウェブカメラ接続テスト
    webcam = WebcamController(camera_index=camera_index)
    
    if webcam.connect():
        print("\n✅ ウェブカメラ接続成功!")
        
        # カメラ情報表示
        info = webcam.get_camera_info()
        print("\nカメラ情報:")
        for key, value in info.items():
            print(f"  {key}: {value}")
        
        # プレビュー表示
        print("\n5秒間プレビューを表示します...")
        webcam.show_preview(duration=5)
        
        # 画像キャプチャ
        print("\n画像をキャプチャします...")
        image = webcam.capture_image()
        
        if image is not None:
            # 画像情報表示
            print(f"画像サイズ: {image.shape}")
            
            # 画像保存
            filepath = webcam.save_image(image)
            if filepath:
                print(f"✅ 画像を保存しました: {filepath}")
            
        # 実験用画像キャプチャテスト
        print("\n実験ステップ画像をキャプチャします...")
        filepath = webcam.capture_and_save("test_step_01")
        if filepath:
            print(f"✅ 実験画像を保存しました: {filepath}")
            
        webcam.disconnect()
        
    else:
        print("❌ ウェブカメラ接続失敗")
        print("\n考えられる原因:")
        print("- ウェブカメラが接続されていない")
        print("- 別のアプリケーションがカメラを使用中")
        print("- カメラドライバーの問題")
        print(f"- 間違ったカメラインデックス（現在: {camera_index}）")
        
    print("\n=== テスト完了 ===")