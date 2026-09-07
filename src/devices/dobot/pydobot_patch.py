"""
pydobot の _read_message をリトライ付きに差し替えるモンキーパッチ

背景:
    pydobot の _read_message() は 100ms 固定で応答を待ち、
    それを超えると None を返す。Dobot の応答が遅れた場合に
    'NoneType' object has no attribute 'params' エラーが散発する。

    このパッチは待機時間を最大 timeout 秒まで延長し、
    poll_interval 間隔でポーリングすることで問題を解消する。
"""

import logging
import time

logger = logging.getLogger(__name__)


def _patched_read_message(self, timeout=2.0, poll_interval=0.05):
    """リトライ付き _read_message。最大 timeout 秒まで応答を待つ。"""
    from pydobot.message import Message

    elapsed = 0.0
    while elapsed < timeout:
        time.sleep(poll_interval)
        elapsed += poll_interval
        b = self.ser.read_all()
        if len(b) > 0:
            msg = Message(b)
            if self.verbose:
                logger.info(f'pydobot: << {msg}')
            return msg
    return None


def apply_pydobot_patch() -> bool:
    """pydobot の _read_message をパッチする。import の直後に1回呼ぶ。

    pydobot 未インストール環境（テスト・モック実行）では import 失敗で
    モジュール全体が読み込めなくなるのを避けるため、False を返すだけにする。
    """
    try:
        from pydobot.dobot import Dobot
    except ImportError:
        logger.warning("pydobot not installed: _read_message patch skipped")
        return False
    Dobot._read_message = _patched_read_message
    return True
