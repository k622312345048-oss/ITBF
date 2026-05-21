"""Tính toán các chỉ số kỹ thuật từ dữ liệu OHLCV đã làm sạch.

Các feature được tính:
- daily_return    : Lợi nhuận theo ngày (%)
- cumulative_ret  : Lợi nhuận tích luỹ từ đầu chuỗi
- ma_7, ma_30     : Đường trung bình động 7 và 30 ngày
- volatility_30   : Độ biến động hoá năm (annualised) 30 ngày
- bb_mid/upper/lower : Bollinger Bands 20 ngày
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

TRADING_DAYS_PER_YEAR = 252


class FeatureEngineer:

    def engineer(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns or df.empty:
            return df

        df = self._daily_returns(df)
        df = self._cumulative_return(df)
        df = self._rolling_averages(df)
        df = self._volatility(df)
        df = self._bollinger_bands(df)

        return df

    # ──────────────────────────────────────────────
    # Private methods
    # ──────────────────────────────────────────────

    def _daily_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Lợi nhuận theo ngày: (close_t - close_{t-1}) / close_{t-1}"""
        df["daily_return"] = df["close"].pct_change()
        return df

    def _cumulative_return(self, df: pd.DataFrame) -> pd.DataFrame:
        """Lợi nhuận tích luỹ từ ngày đầu tiên trong chuỗi."""
        first_close = df["close"].iloc[0]
        if first_close and first_close != 0:
            df["cumulative_ret"] = (df["close"] / first_close) - 1
        return df

    def _rolling_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """MA 7 ngày và MA 30 ngày — đường xu hướng ngắn và trung hạn."""
        df["ma_7"]  = df["close"].rolling(window=7,  min_periods=1).mean()
        df["ma_30"] = df["close"].rolling(window=30, min_periods=1).mean()
        return df

    def _volatility(self, df: pd.DataFrame) -> pd.DataFrame:
        """Độ biến động hoá năm (annualised volatility) dựa trên 30 ngày gần nhất.

        Công thức: std(daily_return, 30 ngày) × sqrt(252)
        Kết quả là % — ví dụ 0.25 = biến động 25%/năm.
        """
        df["volatility_30"] = (
            df["daily_return"]
            .rolling(window=30, min_periods=10)
            .std()
            * np.sqrt(TRADING_DAYS_PER_YEAR)
        )
        return df

    def _bollinger_bands(self, df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        """Bollinger Bands 20 ngày, 2 độ lệch chuẩn.

        bb_mid   = MA 20 ngày
        bb_upper = bb_mid + 2 * std
        bb_lower = bb_mid - 2 * std

        Khi giá chạm bb_upper → có thể quá mua.
        Khi giá chạm bb_lower → có thể quá bán.
        """
        rolling = df["close"].rolling(window=window, min_periods=10)
        df["bb_mid"]   = rolling.mean()
        std            = rolling.std()
        df["bb_upper"] = df["bb_mid"] + 2 * std
        df["bb_lower"] = df["bb_mid"] - 2 * std
        return df
