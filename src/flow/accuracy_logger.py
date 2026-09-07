"""
分注精度ロガー

各 `dispense` の指示量と、その直後の `measure_weight` の測定値を対応させ、
期待重量・誤差・誤差% を CSV に記録する。

期待重量 = 指示量(mL) × 密度(g/mL)
誤差     = 測定重量(g) - 期待重量(g)

天秤は分注前に tare_scale で風袋引きしておく前提（測定値が正味の分注量になる）。
"""
import csv
import os
import statistics
from datetime import datetime


class DispenseAccuracyLogger:
    """dispense と measure_weight を対応させて精度CSVを書き出す。"""

    def __init__(self, csv_path: str, density: float = 1.0):
        self.csv_path = csv_path
        self.density = density
        self._fh = None
        self._writer = None
        self._pending = None  # 直近の dispense 情報
        self._errors = []     # 誤差(g) の履歴（サマリ用）
        self._count = 0

    def _ensure_open(self):
        if self._fh is None:
            os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
            # Excel で文字化けしないよう utf-8-sig
            self._fh = open(self.csv_path, "w", newline="", encoding="utf-8-sig")
            self._writer = csv.writer(self._fh)
            self._writer.writerow([
                "timestamp",
                "iteration",
                "dispense_step",
                "target_volume_mL",
                "speed",
                "density_g_per_mL",
                "expected_weight_g",
                "measured_weight_g",
                "error_g",
                "error_pct",
            ])

    def record_dispense(self, volume, speed=None, iteration=None, step_index=None):
        """dispense アクションの指示量を保留する（次の measure_weight と対応付け）。"""
        self._pending = {
            "volume": volume,
            "speed": speed,
            "iteration": iteration,
            "step_index": step_index,
        }

    def record_weight(self, weight):
        """measure_weight の結果を、保留中の dispense と対応付けて1行書き出す。

        Returns:
            誤差(g)。対応する dispense が無い等で記録しなかった場合は None。
        """
        if self._pending is None or weight is None:
            return None
        p = self._pending
        self._pending = None
        volume = p["volume"]
        if volume is None:
            return None

        expected = volume * self.density
        error = weight - expected
        error_pct = (error / expected * 100.0) if expected else 0.0

        self._ensure_open()
        self._writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            p["iteration"] if p["iteration"] is not None else "",
            p["step_index"] if p["step_index"] is not None else "",
            f"{volume:.4f}",
            p["speed"] if p["speed"] is not None else "",
            f"{self.density:.4f}",
            f"{expected:.4f}",
            f"{weight:.4f}",
            f"{error:+.4f}",
            f"{error_pct:+.2f}",
        ])
        self._fh.flush()
        self._errors.append(error)
        self._count += 1
        return error

    def finalize(self, logger=None):
        """サマリ統計をログ出力し、ファイルを閉じる。"""
        if self._count > 0:
            mean_err = statistics.fmean(self._errors)
            abs_mean = statistics.fmean(abs(e) for e in self._errors)
            stdev = statistics.stdev(self._errors) if self._count > 1 else 0.0
            if logger is not None:
                logger.info(
                    f"分注精度サマリ: n={self._count}, "
                    f"平均誤差={mean_err:+.4f}g, 平均絶対誤差={abs_mean:.4f}g, "
                    f"標準偏差={stdev:.4f}g"
                )
                logger.info(f"精度CSV: {self.csv_path}")
        elif logger is not None:
            logger.info("分注精度データなし（dispense→measure_weight の組が記録されませんでした）")

        if self._fh is not None:
            self._fh.close()
            self._fh = None
            self._writer = None
