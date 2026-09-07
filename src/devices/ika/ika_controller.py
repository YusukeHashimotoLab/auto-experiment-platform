"""
IKA撹拌装置を制御するためのモジュール

このモジュールはIKA RET Control-viscホットスターラーをシリアル通信で制御するための
インターフェースを提供します。温度制御、撹拌速度制御、重量測定など、実験自動化に
必要な機能をサポートしています。

使用方法:
    from ika.ika_controller import IKAController
    
    # IKAコントローラーの初期化
    device = IKAController(port='COM8')
    
    # 温度と撹拌速度を設定して撹拌開始（摂氏40度、速度100rpm）
    device.start_stirring(40, 100)
    
    # 5分間撹拌
    time.sleep(300)
    
    # 撹拌停止
    device.stop_stirring()
    
    # 接続を閉じる
    device.close()
    
"""

import logging
import os
import time
from datetime import datetime
import serial

logger = logging.getLogger(__name__)


def _get_pyplot():
    """matplotlib を遅延 import する（グラフ表示メソッドからのみ使用）。

    以前は import 時に ``matplotlib.use("TkAgg")`` を実行していたため、
    ドライバを import するだけで Tk（GUI）が必要になっていた。
    ヘッドレス環境やテストで import できなくなるのを避けるため遅延化した。
    """
    import matplotlib

    try:
        matplotlib.use("TkAgg")  # 環境によって"Qt5Agg"に変更が必要な場合あり
    except Exception as e:  # GUI バックエンドが無い環境ではそのまま既定を使う
        logger.warning(f"matplotlib backend 'TkAgg' を使用できません: {e}")

    import matplotlib.pyplot as plt

    return plt


class IKAController:
    """
    IKA RET Control-viscホットスターラーを制御するクラス
    
    このクラスはIKAのホットスターラーをシリアル通信で制御するための機能を提供します。
    温度制御、撹拌速度制御、データ記録などの機能を備えています。
    """
    
    def __init__(self, port='COM8', baudrate=9600, timeout=1):
        """
        IKAControllerを初期化する
        
        Args:
            port (str): シリアルポート名。デフォルト: 'COM8'
            baudrate (int): 通信速度。デフォルト: 9600
            timeout (int): 通信タイムアウト（秒）。デフォルト: 1
        """
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout
        )

    def is_connected(self):
        """
        接続状態を確認する
        
        Returns:
            bool: 接続されているかどうか
        """
        return self.ser.is_open

    def connect(self):
        """シリアルポートを開く（既に開いていれば何もしない）

        ``__init__`` の時点でポートは開かれるため冪等な薄いラッパだが、
        上位層（LabRobot）が期待する connect()/disconnect() インタフェースを
        揃えるために提供する。

        Returns:
            bool: 接続できたかどうか
        """
        if not self.ser.is_open:
            self.ser.open()
            logger.info("シリアルポートを開きました。")
        return self.ser.is_open

    def disconnect(self):
        """シリアルポートを閉じる（``close()`` のエイリアス）

        Returns:
            bool: 切断できたかどうか
        """
        if self.ser.is_open:
            self.close()
        return not self.ser.is_open

    def send_command(self, command):
        """
        デバイスにコマンドを送信し、応答を受け取る
        
        Args:
            command (str): 送信するコマンド
            
        Returns:
            str: 受信した応答
        """
        self.ser.write((command + '\r\n').encode())  # コマンドを送信
        time.sleep(0.5)  # 応答を待つ
        response = self.ser.read(self.ser.in_waiting).decode()  # レスポンスを読み取る
        return response

    def reset_device(self):
        """
        デバイスをリセットする
        """
        logger.info("デバイスをリセットしています...")
        self.send_command('RESET')
        time.sleep(2)  # リセット後少し待機

    def start_pc_mode(self, X):
        """
        PCモードを開始する
        
        Args:
            X (int): 制御モード番号（2:温度、4:撹拌、90:重量など）
        """
        logger.info(f"PCモード {X} を開始しています...")
        self.send_command(f'START_{X}')

    def check_weight_function_ready(self):
        """
        重量測定機能の準備ができているか確認する
        
        Returns:
            bool: 重量測定機能が準備できているかどうか
        """
        logger.info("重量測定機能の準備状況を確認しています...")
        status = self.send_command('STATUS_90')
        logger.info(f"ステータス: {status}")

        # 準備ができていれば '1041 90' が返る
        return '1041 90' in status

    def wait_for_weight_function_ready(self, max_wait_time=60, check_interval=2):
        """
        重量測定機能が準備できるまで待機する
        
        Args:
            max_wait_time (int): 最大待機時間（秒）。デフォルト: 60
            check_interval (int): 状態確認の間隔（秒）。デフォルト: 2
            
        Returns:
            bool: 重量測定機能が準備できたかどうか
        """
        logger.info("重量測定機能の準備完了を待機しています...")
        elapsed_time = 0
        while elapsed_time < max_wait_time:
            if self.check_weight_function_ready():
                logger.info("重量測定機能の準備ができました。")
                return True
            time.sleep(check_interval)
            elapsed_time += check_interval
            logger.info(f"{elapsed_time}秒経過...")

        logger.error("最大待機時間内に重量測定機能の準備ができませんでした。")
        return False

    def read_data(self, X):
        """
        装置からデータを読み取る
        
        Args:
            X (int): 読み取りモード番号（2:温度、4:撹拌、90:重量など）
            
        Returns:
            str: 読み取ったデータ
        """
        data = self.send_command(f'IN_PV_{X}')
        return data

    def set_stirring_speed(self, speed):
        """
        撹拌速度を設定する
        
        Args:
            speed (int): 撹拌速度（rpm）
        """
        logger.info(f"撹拌速度を {speed} rpmに設定しています...")
        self.send_command(f'OUT_SP_4 {speed}')

    def stop_pc_mode(self, X):
        """
        PCモードを停止する
        
        Args:
            X (int): 停止するモード番号（2:温度、4:撹拌、90:重量など）
        """
        logger.info(f"PCモード {X} を停止しています...")
        self.send_command(f'STOP_{X}')

    def close(self):
        """
        シリアルポートを閉じる
        """
        self.ser.close()
        logger.info("シリアルポートを閉じました。")

    def start_stirring(self, temperature, speed):
        """
        指定した温度と速度で撹拌を開始する
        
        Args:
            temperature (float): 設定温度（摂氏）
            speed (int): 撹拌速度（rpm）
        """
        # 温度と撹拌速度を設定
        self.send_command(f'OUT_SP_2 {temperature}')
        self.send_command(f'OUT_SP_4 {speed}')

        # 温度制御と撹拌を開始
        self.start_pc_mode(2)
        self.start_pc_mode(4)
        logger.info(f'温度 {temperature}℃、速度 {speed}rpmでの撹拌を開始しました')

    def stop_stirring(self):
        """
        撹拌と温度制御を停止する
        """
        logger.info('撹拌を停止しています。')
        self.stop_pc_mode(4)  # 撹拌停止
        self.stop_pc_mode(2)  # 温度制御停止

    def set_temperature(self, temperature, speed, wait_minute):
        """
        温度と撹拌速度を設定し、指定時間動作させる（グラフ表示あり）
        
        Args:
            temperature (float): 設定温度（摂氏）
            speed (int): 撹拌速度（rpm）
            wait_minute (float): 動作時間（分）
            
        Returns:
            tuple: (温度リスト, 時間リスト)
        """
        # 温度と撹拌速度を設定
        self.send_command(f'OUT_SP_2 {temperature}')
        self.send_command(f'OUT_SP_4 {speed}')

        # 温度制御と撹拌を開始
        self.start_pc_mode(2)
        self.start_pc_mode(4)
        logger.info(f'温度 {temperature}℃ での撹拌を制御しています')

        # データ収集用のリスト
        temperatures = []
        times = []
        start_time = time.time()

        # リアルタイムグラフ表示の準備（matplotlib は必要になった時点で読み込む）
        plt = _get_pyplot()
        plt.ion()
        fig, ax = plt.subplots()
        ax.set_title("温度モニタリング")
        ax.set_xlabel("時間（分）")
        ax.set_ylabel("温度（°C）")

        # 指定時間の間、温度をモニタリング
        while (time.time() - start_time) < wait_minute * 60:
            temp_data = self.read_data(2).strip()
            try:
                temperature_value = float(temp_data.split()[0])
                temperatures.append(temperature_value)
                times.append((time.time() - start_time)/60)

                # グラフの更新
                ax.clear()
                ax.plot(times, temperatures, label="温度", color="blue")
                ax.legend()
                ax.set_title("温度モニタリング")
                ax.set_xlabel("時間（分）")
                ax.set_ylabel("温度（°C）")

                plt.draw()
                plt.pause(1)
                plt.gcf().canvas.flush_events()  # リアルタイム更新を強制
            except ValueError:
                logger.error(f"データを浮動小数点に変換できませんでした: {temp_data}")

        # 終了処理
        logger.info('撹拌が完了しました。')
        self.stop_pc_mode(4)
        self.stop_pc_mode(2)
        plt.ioff()

        return temperatures, times

    def stirring_at_temperature(self, temperature, speed, wait_minute):
        """
        温度と撹拌速度を設定し、指定時間動作させる（グラフ表示なし）
        
        Args:
            temperature (float): 設定温度（摂氏）
            speed (int): 撹拌速度（rpm）
            wait_minute (float): 動作時間（分）
        """
        # 温度と撹拌速度を設定
        self.send_command(f'OUT_SP_2 {temperature}')
        self.send_command(f'OUT_SP_4 {speed}')

        # 温度制御と撹拌を開始
        self.start_pc_mode(2)
        self.start_pc_mode(4)
        logger.info(f'温度 {temperature}℃ での撹拌を開始しました')
        
        # 指定時間待機
        time.sleep(wait_minute * 60)
        
        # 終了処理
        logger.info('撹拌が完了しました。')
        self.stop_pc_mode(4)
        self.stop_pc_mode(2)

    def measure_weight(self):
        """
        装置の計量機能で重量を測定する
        
        Returns:
            str: 測定された重量データ
        """
        weight = 0
        # 最大10回試行
        for i in range(10):
            status = self.send_command(f'STATUS_90')
            if str(status).strip() == '1041 90':
                weight = self.send_command('IN_PV_90')
                break
            else:
                time.sleep(1)

        # 計量モードを停止
        self.send_command(f'STOP_1')
        self.send_command(f'STOP_90')

        return weight


def run_temperature_experiment(device, params):
    """
    温度実験を実行する関数
    
    Args:
        device (IKAController): IKAコントローラーインスタンス
        params (dict): 実験パラメータ辞書
        
    Returns:
        tuple: (温度リスト, 時間リスト)
    """
    # パラメータを取得
    temperature = params.get("temperature")
    stabilize_speed = params.get("stabilize_speed")
    stabilize_minute = params.get("stabilize_minute")
    stirring_speed = params.get("stirring_speed")
    stirring_minute = params.get("stirring_minute")

    # 安定化フェーズ
    device.set_temperature(temperature, stabilize_speed, stabilize_minute)

    # 撹拌フェーズ
    temperatures, times = device.set_temperature(temperature, stirring_speed, stirring_minute)

    return temperatures, times


if __name__ == '__main__':
    """
    IKAControllerの使用例
    """
    # 設定パラメータ
    temperature = 40  # 摂氏温度
    speed = 100       # 撹拌速度（rpm）

    # IKAコントローラーの初期化
    port_name = 'COM17'
    device = IKAController(port=port_name)

    # 温度モードを開始
    device.send_command(f'START_2')
    
    # 温度制御と撹拌を開始
    device.start_stirring(temperature, speed)
    
    # 実験終了後は手動で停止する必要あり