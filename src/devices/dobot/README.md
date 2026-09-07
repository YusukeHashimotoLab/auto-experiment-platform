# Dobotロボットアーム制御モジュール

Dobot Magician を `pydobot` ライブラリ経由（シリアル通信）で制御するドライバです。
各インスタンスが独立したシリアル接続を持つため、複数台の Dobot を同時に制御できます。

## ファイル

| ファイル | 役割 |
|---|---|
| `pydobot_controller.py` | `PyDobotController` — 本体 |
| `pydobot_patch.py` | pydobot の不足コマンド（スライダー・コンベア等）を補うパッチ |
| `dobot_config.py` | 速度プリセット・作業位置の定義（`DobotConfig`） |

## 使用例

```python
from src.devices.dobot import PyDobotController

# ポート名を指定して接続（Windows: 'COM12', Linux/macOS: '/dev/ttyUSB0' など）
robot = PyDobotController(port_name='COM12', homing=False)

robot.move_XYZ_abs(200, 0, 100)   # 絶対座標へ移動
robot.move_Z(-50)                 # Z 相対移動
robot.move_XY(20, 30)             # XY 相対移動
robot.move_angle(45)              # ベース（Joint1）角度
print(robot.get_current_position())

robot.disconnect()
```

利用可能なシリアルポートの一覧:

```python
PyDobotController.list_available_ports()
```

## 主なメソッド

| メソッド | 説明 |
|---|---|
| `move_XYZ_abs(x, y, z, r=None)` | 絶対座標へ移動 |
| `move_Z(z_offset)` / `move_XY(dx, dy)` | 相対移動 |
| `move_angle(angle)` | Joint1 の絶対角度 |
| `move_to_initial_pos()` | 初期位置へ |
| `pickup(...)` / `place(...)` | ピックアンドプレース |
| `set_gripper(enabled, on)` / `set_suction_cup(enabled, on)` | エンドエフェクタ |
| `set_speed_preset(name)` | `DobotConfig.SPEED_PRESETS` の速度に切替 |
| `move_to_work_position(name)` / `set_home_params(x, y, z, r)` | 定義済み位置 |
| `move_slider(pos)` | リニアレール（0–1000 mm） |
| `move_conveyer(index, speed, time_seconds)` | コンベアベルト |
| `get_current_position()` | `[x, y, z, r]` |
| `disconnect()` | 切断 |

## 注意点

- 自動運転の前に、手動で可動域と周囲の安全を確認してください。
- `homing=True` を指定するとホーミング動作で腕が動きます。障害物がないことを確認してください。
- 実験用の安全ラッパ（`src/devices/safety/lab_robot.py`）はこのクラスを内部で使い、
  可動域チェックと待機時間を追加します。フロー実行時はラッパ経由で呼び出されます。
- モーターから異音がした場合は直ちに `disconnect()` して物理的な干渉を確認してください。

## 依存関係

- `pydobot`（MIT License、`THIRD_PARTY_NOTICES.md` 参照）
- `pyserial`

Dobot 純正 DLL（DobotDll）を用いる旧ドライバはライセンス上の理由で本リポジトリには含めていません。
