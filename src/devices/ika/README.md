# IKA撹拌装置制御モジュール

このモジュールは実験自動化システムにおいてIKA RET Control-viscホットスターラーをシリアル通信で制御するためのクラスと関数を提供します。

## 概要

`ika_controller.py`はIKAホットスターラーを操作するためのインターフェースを提供します。主な機能には以下が含まれます：

- シリアル接続管理
- 温度制御
- 撹拌速度制御
- 重量測定（RET control-visc のみ。下記の注意を参照）
- データ記録とグラフ表示

このモジュールを使用することで、実験の温度・撹拌を正確に制御し、リアルタイムでのモニタリングが可能になります。

## 使用方法

### 基本的な使用例

```python
from src.devices.ika.ika_controller import IKAController
import time

# IKAコントローラーの初期化（ポート名を指定）
device = IKAController(port='COM8')

# デバイスのリセット（任意）
device.reset_device()

# 温度と撹拌速度を設定して撹拌開始（摂氏40度、速度100rpm）
device.start_stirring(40, 100)

# 5分間撹拌
time.sleep(300)

# 撹拌停止
device.stop_stirring()

# 接続を閉じる
device.close()
```

### 温度制御とモニタリング

```python
# 温度40℃、撹拌速度100rpmで10分間動作（グラフ表示あり）
temperatures, times = device.set_temperature(40, 100, 10)

# 温度40℃、撹拌速度100rpmで10分間動作（グラフ表示なし）
device.stirring_at_temperature(40, 100, 10)
```

### 重量測定

```python
# 重量を測定
weight = device.measure_weight()
print(f"測定された重量: {weight}")
```

### 実験パラメータを使用した制御

```python
from src.devices.ika.ika_controller import IKAController, run_temperature_experiment

# IKAコントローラーの初期化
device = IKAController(port='COM17')

# 実験パラメータの定義
params = {
    "temperature": 45,        # 設定温度（℃）
    "stabilize_speed": 200,   # 安定化フェーズでの撹拌速度（rpm）
    "stabilize_minute": 5,    # 安定化フェーズの時間（分）
    "stirring_speed": 150,    # 撹拌フェーズでの撹拌速度（rpm）
    "stirring_minute": 15     # 撹拌フェーズの時間（分）
}

# 実験の実行
temperatures, times = run_temperature_experiment(device, params)

# データをPandasデータフレームに変換してCSVに保存
import pandas as pd
data = pd.DataFrame({
    "Time (minutes)": times,
    "Temperature (°C)": temperatures
})
data.to_csv("experiment_data.csv", index=False)
```

## 主要機能

### 接続管理

- `__init__(port, baudrate, timeout)` - コントローラーの初期化とシリアル接続
- `is_connected()` - 接続状態を確認する
- `send_command(command)` - コマンドを送信する
- `close()` - シリアルポートを閉じる

### デバイス制御

- `reset_device()` - デバイスをリセットする
- `start_pc_mode(X)` - PCモードを開始する（X：モード番号）
- `stop_pc_mode(X)` - PCモードを停止する（X：モード番号）
- `read_data(X)` - 装置からデータを読み取る（X：読み取りモード番号）

### 撹拌と温度制御

- `set_stirring_speed(speed)` - 撹拌速度を設定する
- `start_stirring(temperature, speed)` - 温度と撹拌速度を設定して撹拌開始
- `stop_stirring()` - 撹拌と温度制御を停止する
- `set_temperature(temperature, speed, wait_minute)` - 温度と撹拌速度を設定し、指定時間動作させる（グラフ表示あり）
- `stirring_at_temperature(temperature, speed, wait_minute)` - 温度と撹拌速度を設定し、指定時間動作させる（グラフ表示なし）

### 重量測定

- `check_weight_function_ready()` - 重量測定機能の準備状況を確認する
- `wait_for_weight_function_ready(max_wait_time, check_interval)` - 重量測定機能が準備できるまで待機する
- `measure_weight()` - 装置の計量機能で重量を測定する

### 実験ユーティリティ

- `run_temperature_experiment(device, params)` - 温度実験を実行する関数

## IKAコマンド仕様

以下に主要なIKAコマンドを示します：

- `RESET` - デバイスをリセットする
- `START_X` - PCモードXを開始する（X：モード番号）
- `STOP_X` - PCモードXを停止する（X：モード番号）
- `IN_PV_X` - モードXの現在値を読み取る（X：モード番号）
- `OUT_SP_X Y` - モードXの設定値をYに設定する（X：モード番号、Y：設定値）
- `STATUS_X` - モードXの状態を取得する（X：モード番号）

### モード番号

- `2` - 温度制御モード
- `4` - 撹拌速度制御モード
- `90` - 重量測定モード

## データ記録とグラフ表示

`set_temperature()`メソッドは実験中の温度データをリアルタイムでグラフ表示し、実験終了後にデータを返します。このデータはCSVファイルに保存するなど、さらなる分析に利用できます。

```python
# データをCSVに保存
import pandas as pd
import os
from datetime import datetime

# 現在の日時をフォルダ名として使用
current_time = datetime.now().strftime("%Y%m%d_%H%M")
folder_name = f"data_{current_time}"
os.makedirs(folder_name, exist_ok=True)

data = pd.DataFrame({
    "Time (minutes)": times,
    "Temperature (°C)": temperatures
})

file_name = "temperature_data.csv"
data.to_csv(os.path.join(folder_name, file_name), index=False)
```

## 注意点

- **重量測定機能は実験フローでは使っていません。** RET control-visc 内蔵の計量機能は
  計量範囲 10–5000 g、精度 ±(0.3 % + 2) g（IKA 公表値）で、数 g の分注量を評価するには
  粗すぎます。質量測定はすべて電子天秤（`src/devices/scale/`）で行います。
  `measure_weight()` 等は RET control-visc でしか動作せず、互換性のために残してあるだけです。
  撹拌・温度制御のコマンド（`OUT_SP_2`, `OUT_SP_4`, `START_x`, `STOP_x`, `IN_PV_x`）は
  IKA の NAMUR コマンド共通なので、RS-232/USB 付きの安価な機種（例: IKA Plate (RCT digital)）
  でも使えるはずです。ただし RCT digital での動作確認はまだ行っていません。
- シリアルポート名（COM8など）は環境によって異なります。デバイスマネージャーなどで確認してください。
- 温度制御は外部環境の影響を受けるため、設定温度に到達するまでに時間がかかる場合があります。
- 長時間の実験では、データのバックアップを定期的に行うことをお勧めします。
- 撹拌速度は0〜1000rpmの範囲で設定可能ですが、液体の粘度や容器によって適切な値は異なります。

## 依存関係

- `serial` - シリアル通信
- `time` - 時間制御
- `matplotlib` - グラフ表示
- `pandas` - データ処理（オプション）
- `datetime` - 日時処理
- `os` - ファイル操作

## トラブルシューティング

- 接続エラーが発生した場合、正しいポート名を指定しているか、デバイスの電源が入っているかを確認してください。
- グラフ表示に問題がある場合、`matplotlib.use("TkAgg")`を環境に合わせて変更してください（例：`Qt5Agg`）。
- 温度が安定しない場合、周囲環境や使用する液体の量、容器の材質を確認してください。