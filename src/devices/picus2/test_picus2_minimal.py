"""
Picus2電動ピペット 最小限の動作確認スクリプト

使い方:
    python test_picus2_minimal.py
"""

import asyncio
from picus2_controller import Picus2Controller, ConnectionType, Buttons


async def minimal_test():
    """最小限の動作確認"""

    # === 設定 ===
    COM_PORT = "COM3"  # 使用するCOMポートに変更してください

    print("=" * 50)
    print("Picus2 最小限動作確認")
    print("=" * 50)

    # コントローラー初期化
    picus = Picus2Controller(COM_PORT, connection_type=ConnectionType.USB)
    picus.DEBUG = True  # デバッグ出力を有効化

    try:
        # 1. 接続
        print("\n[1] 接続中...")
        connected = await picus.connect()
        if not connected:
            print("接続失敗。COMポートを確認してください。")
            return
        print("接続成功!")

        # 2. モーターモード有効化
        print("\n[2] モーターモード有効化...")
        await picus.set_motor_mode(True)
        print("モーターモード有効!")

        # 3. 少量の吸引テスト (0.5mL)
        print("\n[3] 吸引テスト (0.5mL)...")
        await picus.aspirate(amount=0.5, speed=5)
        print("吸引完了!")

        await asyncio.sleep(1)

        # 4. 少量の吐出テスト (0.5mL)
        print("\n[4] 吐出テスト (0.5mL)...")
        await picus.dispense(amount=0.5, speed=5)
        print("吐出完了!")

        # 5. モーターモード無効化
        print("\n[5] モーターモード無効化...")
        await picus.button(Buttons.TRIGGER_BUTTON_LEFT)
        await picus.button(Buttons.TRIGGER_BUTTON_RIGHT)
        print("モーターモード無効化完了!")

        print("\n" + "=" * 50)
        print("動作確認成功!")
        print("=" * 50)

    except Exception as e:
        print(f"\nエラー発生: {e}")

    finally:
        # 6. 切断
        print("\n[6] 切断中...")
        await picus.disconnect()
        print("切断完了!")


if __name__ == "__main__":
    asyncio.run(minimal_test())
