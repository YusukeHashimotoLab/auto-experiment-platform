# 電子天びん制御モジュール

A&D EK-610i 系電子天びんをRS-232C経由で操作するためのコントローラーです。

## 特徴

- **高精度測定**: 0.01g精度での重量測定
- **安定化測定**: 複数回測定による平均値取得
- **風袋引き機能**: ゼロ点リセット機能
- **コンテキストマネージャー対応**: 自動接続・切断管理
- **エラーハンドリング**: 包括的な例外処理

## 使用方法

### 基本的な使用例

```python
from src.devices.scale import ScaleController

# コンテキストマネージャーとして使用（推奨）
with ScaleController(port="COM3") as scale:
    # 風袋引き
    scale.tare()
    
    # 重量測定
    weight = scale.query_weight()
    print(f"重量: {weight:.3f} g")
    
    # 安定した重量取得
    stable_weight = scale.get_stable_weight(samples=5)
    print(f"安定重量: {stable_weight:.3f} g")
```

### 手動接続・切断

```python
scale = ScaleController(port="COM3")

try:
    # 接続
    if scale.connect():
        # 測定
        weight = scale.query_weight()
        print(f"重量: {weight:.3f} g")
finally:
    # 切断
    scale.disconnect()
```

## API リファレンス

### ScaleController

電子天びん制御のメインクラス

#### コンストラクタ

```python
ScaleController(port="COM3", baudrate=2400, bytesize=7, parity="even", stopbits=1)
```

#### メソッド

- `connect() -> bool`: デバイスに接続
- `disconnect()`: デバイスから切断  
- `is_connected() -> bool`: 接続状態確認
- `query_weight() -> float`: 重量測定（単発）
- `tare(delay=0.5) -> bool`: 風袋引き
- `get_stable_weight(samples=3, interval=0.1) -> float`: 安定重量測定

## 通信仕様

- **ポート**: RS-232C
- **ボーレート**: 2400 bps
- **データビット**: 7 bit
- **パリティ**: Even
- **ストップビット**: 1 bit
- **フロー制御**: なし

## エラー処理

以下の例外が発生する可能性があります：

- `ConnectionError`: デバイス接続エラー
- `TimeoutError`: 応答タイムアウト
- `ValueError`: データ解析エラー

## ログ

デバッグレベルでの詳細ログと、INFOレベルでの操作ログを出力します。

```python
import logging
logging.basicConfig(level=logging.INFO)
```