import logging
import serial
import re  # 正規表現モジュール

logger = logging.getLogger(__name__)


class SerialBalance:
    def __init__(self, port='COM4', baudrate=9600, timeout=1):
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            parity=serial.PARITY_ODD,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=timeout
        )

    def get_weight(self):
        """天びんから重量データを取得

        Returns:
            float | None: 重量(g)。数値が読めなかった場合は None
        """
        self.ser.write(b'P\r\n')  # PRINTコマンドを送信
        raw = self.ser.readline()
        weight_data = raw.decode('ascii', errors='replace').strip()  # データを読み取り、ASCII形式でデコード
        number = self.extract_number(weight_data)  # 数値部分を抽出
        if number is None:
            logger.warning(f"天びんの応答から重量を読み取れませんでした: {weight_data!r}")
        return number

    def extract_number(self, data):
        r"""重量データから数値部分を抽出する。

        Sartorius BCE のプリントアウトは
            ``[安定/種別マーカー] [符号] [空白...] 数値 [空白] 単位``
        の固定幅フォーマットで、符号と数字の間に空白が入る
        （例: ``'-     0.03 g'`` / ``'N  +  0.00 g'``）。
        旧実装の ``[-+]?\d*\.\d+`` は符号と数字が隣接している場合しか拾えず、
        負の重量が正として返っていた。

        Returns:
            float | None: 抽出した数値（符号付き）。見つからない場合は None
        """
        if not data:
            return None
        match = re.search(r"([-+])?\s*(\d+(?:\.\d+)?|\.\d+)", data)
        if not match:
            return None
        sign = -1.0 if match.group(1) == "-" else 1.0
        return sign * float(match.group(2))

    def tare(self):
        """風袋引き（ゼロ点リセット）を実行"""
        self.ser.write(b'T\r\n')  # TAREコマンドを送信

    def close(self):
        """シリアル通信を終了"""
        self.ser.close()


if __name__ == '__main__':
    port_num = 'COM4'

    try:
        balance = SerialBalance(port=port_num)  # インスタンス作成
        weight = balance.get_weight()  # 重量データ取得
        print(f"抽出された数値: {weight}")
    finally:
        balance.close()  # 通信終了
