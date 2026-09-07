"""
A&D EK-610i 電子天びん制御クラス

精密重量測定とリアルタイム監視機能を提供します。
"""

import serial
import time
import re
import logging
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


def _signed_float(match) -> float:
    r"""``([+-])?\s*(数値)`` 形式のマッチを符号付き float に変換する。

    天びんによっては符号と数字の間に空白が入る（例: ``'ST,-  0.03 g'``）ため、
    符号と数値を別グループで受け取る。
    """
    sign = -1.0 if match.group(1) == "-" else 1.0
    return sign * float(match.group(2))


class ScaleController:
    """
    A&D EK-610i 系電子天びんを RS-232C 経由で操作するクラス。
    コンテキストマネージャ対応で、自動的にポートを開閉します。
    """

    DEFAULT_PORT = "COM3"
    DEFAULT_BAUD = 2400
    DEFAULT_BYTESIZE = serial.SEVENBITS
    DEFAULT_PARITY = serial.PARITY_EVEN
    DEFAULT_STOPBITS = serial.STOPBITS_ONE
    READ_TIMEOUT = 10    # 秒
    WRITE_TIMEOUT = 3    # 秒

    def __init__(self,
                 port: str = DEFAULT_PORT,
                 baudrate: int = DEFAULT_BAUD,
                 bytesize: int = DEFAULT_BYTESIZE,
                 parity: str = DEFAULT_PARITY,
                 stopbits: int = DEFAULT_STOPBITS):
        """
        電子天びんコントローラーを初期化する

        Args:
            port: シリアルポート名 (デフォルト: COM3)
            baudrate: ボーレート (デフォルト: 2400)
            bytesize: データビット数 (デフォルト: 7bit)
            parity: パリティ (デフォルト: Even)
            stopbits: ストップビット (デフォルト: 1)
        """
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self._ser: Optional[serial.Serial] = None
        self._connected = False

    def __enter__(self):
        """コンテキストマネージャーとして使用時の接続処理"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーとして使用時の切断処理"""
        self.disconnect()

    def connect(self) -> bool:
        """
        電子天びんに接続する

        Returns:
            接続成功時True、失敗時False
        """
        try:
            self._ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.READ_TIMEOUT,
                write_timeout=self.WRITE_TIMEOUT,
            )
            self._connected = True
            logger.info(f"電子天びんに接続しました (ポート: {self.port})")
            return True
        except Exception as e:
            logger.error(f"電子天びんへの接続に失敗しました: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """電子天びんから切断する"""
        if self._ser and self._ser.is_open:
            self._ser.close()
            self._connected = False
            logger.info("電子天びんから切断しました")

    def is_connected(self) -> bool:
        """接続状態を確認する"""
        return self._connected and self._ser and self._ser.is_open

    def _send_command(self, cmd: bytes):
        """
        CR+LF 終端付きでコマンドを送信し、バッファをクリア→フラッシュ

        Args:
            cmd: 送信するコマンド（バイト列）
        """
        if not self.is_connected():
            raise ConnectionError("電子天びんが接続されていません")
        
        self._ser.reset_input_buffer()#これまでの受信バッファをクリア
        self._ser.reset_output_buffer()
        time.sleep(0.1)  # コマンド送信前に少し待機
        self._ser.write(cmd + b"\r\n")#\r\nはenterみたいなもの
        self._ser.flush()
        time.sleep(0.2)  # コマンド送信後に少し待機

    def query_weight(self) -> float:
        """
        計量値を要求し、float で返却。
        応答がなければ TimeoutError を投げる。

        Returns:
            重量値（グラム）

        Raises:
            TimeoutError: 応答がない場合
            ValueError: 値の解析に失敗した場合
        """
        retry_count = 3
        for attempt in range(retry_count):
            try:
                self._send_command(b"Q")
                
                # 複数行読み取りを試行
                raw = ""
                for read_attempt in range(5):  # 最大5回読み取り試行
                    line = self._ser.readline().decode("ascii", errors="ignore").strip()
                    logger.debug(f"読み取り試行 {read_attempt + 1}: '{line}' (長さ: {len(line)})")
                    if line:
                        raw = line
                        break
                    time.sleep(0.2)  # 読み取り間隔を延長
                
                if not raw:
                    if attempt < retry_count - 1:
                        logger.warning(f"天びんからの応答なし (試行 {attempt + 1}/{retry_count})")
                        time.sleep(0.5)
                        continue
                    else:
                        raise TimeoutError("天びんから応答がありません")
                
                logger.debug(f"天びん応答: {raw}")
                
                # 例: "ST,+000123.45 g"
                if "," not in raw:
                    # カンマがない場合の処理
                    num_match = re.search(r'([+-])?\s*(\d+\.?\d*)', raw)
                    if num_match:
                        weight = _signed_float(num_match)
                        logger.debug(f"重量測定: {weight:.3f} g")
                        return weight
                    else:
                        raise ValueError(f"重量値の解析に失敗しました: {raw}")
                
                header, val_unit = raw.split(",", 1)
                
                # 数字部分だけ抽出（負号も含む）
                num_match = re.search(r'([+-])?\s*(\d+\.?\d*)', val_unit)
                if not num_match:
                    raise ValueError(f"重量値の解析に失敗しました: {raw}")
                
                weight = _signed_float(num_match)
                logger.debug(f"重量測定: {weight:.3f} g")
                return weight
                
            except (TimeoutError, ValueError) as e:
                if attempt < retry_count - 1:
                    logger.warning(f"重量測定エラー (試行 {attempt + 1}/{retry_count}): {e}")
                    time.sleep(0.5)
                    continue
                else:
                    logger.error(f"重量測定エラー: {e}")
                    raise
            except Exception as e:
                logger.error(f"重量測定エラー: {e}")
                raise

    def tare(self, delay: float = 5.0) -> bool:
        """
        風袋引き（ゼロ点）コマンド。
        delay 秒だけ待ってから戻る。

        Args:
            delay: 待機時間（秒）

        Returns:
            処理成功時True
        """
        try:
            self._send_command(b"R")
            time.sleep(delay)
            logger.info("風袋引きを実行しました")
            return True
        except Exception as e:
            logger.error(f"風袋引きエラー: {e}")
            return False

    def get_stable_weight(self, samples: int = 3, interval: float = 0.1) -> float:
        """
        安定した重量値を取得する（複数回測定の平均）

        Args:
            samples: 測定回数
            interval: 測定間隔（秒）

        Returns:
            平均重量値（グラム）
        """
        weights = []
        for _ in range(samples):
            weight = self.query_weight()
            weights.append(weight)
            if interval > 0:
                time.sleep(interval)
        
        avg_weight = sum(weights) / len(weights)
        logger.debug(f"安定重量測定 ({samples}回平均): {avg_weight:.3f} g")
        return avg_weight


if __name__ == "__main__":
    # テスト実行
    print("Electronic Scale Controller Test")
    print("Connecting to scale...")
    
    try:
        with ScaleController(port="COM3") as scale:
            print("Successfully connected to scale!")
            
            # 風袋引き
            print("Performing tare (zero calibration)...")
            scale.tare()
            time.sleep(1)

            # 重量取得
            print("Reading current weight...")
            weight = scale.query_weight()
            print(f"Current weight: {weight:.2f} g")

            # 安定重量取得
            print("Measuring stable weight (5 samples)...")
            stable_weight = scale.get_stable_weight(samples=5)
            print(f"Stable weight: {stable_weight:.3f} g")
            
            print("Weight measurement completed!")
            
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        print("Please check:")
        print("- Scale is connected and powered on")
        print("- COM port is correct (currently set to COM3)")
        print("- Scale is properly configured for RS-232 communication")