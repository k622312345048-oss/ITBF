"""Làm sạch dữ liệu tài chính thô.

Xử lý các vấn đề phổ biến:
- Missing values  → forward-fill (giữ giá trị gần nhất)
- Duplicate dates → giữ bản ghi đầu tiên
- Kiểu dữ liệu   → chuẩn hoá về float/datetime
- Giá bằng 0      → thay bằng NaN rồi forward-fill
- Outliers        → đánh dấu cột is_outlier (không xoá)
"""

import logging
from pathlib import Path

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

PRICE_COLS = ["open", "high", "low", "close"]


class Cleaner:

    def clean(self, filepath: Path) -> pd.DataFrame:
        """Đọc và làm sạch 1 file CSV thô.

        Trả về DataFrame với:
        - Index là DatetimeIndex tên 'date', sắp xếp tăng dần
        - Columns: open, high, low, close, volume
        """
        name = filepath.stem
        df = self._load(filepath)
        if df.empty:
            logger.warning(f"[{name}] File rỗng, bỏ qua.")
            return df

        original_len = len(df)

        df = self._normalize_types(df)
        df = self._remove_zero_prices(df, name)
        df = self._remove_duplicates(df, name)
        df = self._handle_missing(df, name)
        df = self._flag_outliers(df, name)
        df = df.sort_index()

        logger.debug(f"[{name}] {original_len} → {len(df)} rows "
                     f"({df.index[0].date()} → {df.index[-1].date()})")
        return df

    # ──────────────────────────────────────────────
    # Private methods
    # ──────────────────────────────────────────────

    def _load(self, filepath: Path) -> pd.DataFrame:
        """Đọc file, tự nhận biết format vnstock vs yfinance."""
        df = pd.read_csv(filepath)

        # vnstock: cột đầu tiên tên 'time'
        if "time" in df.columns:
            df = df.rename(columns={"time": "date"})
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.set_index("date")
        else:
            # yfinance: cột đầu tiên là index (date)
            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            df.index.name = "date"

        df.columns = df.columns.str.lower()
        return df

    def _normalize_types(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in PRICE_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)
        return df

    def _remove_zero_prices(self, df: pd.DataFrame, name: str) -> pd.DataFrame:
        """Giá bằng 0 là lỗi dữ liệu (trading halt thường để NaN, không phải 0)."""
        if "close" not in df.columns:
            return df
        zero_mask = df["close"] == 0
        n = zero_mask.sum()
        if n:
            df.loc[zero_mask, PRICE_COLS] = np.nan
            logger.debug(f"[{name}] Thay {n} dòng giá=0 bằng NaN → sẽ forward-fill.")
        return df

    def _remove_duplicates(self, df: pd.DataFrame, name: str) -> pd.DataFrame:
        before = len(df)
        df = df[~df.index.duplicated(keep="first")]
        removed = before - len(df)
        if removed:
            logger.debug(f"[{name}] Xoá {removed} dòng trùng ngày.")
        return df

    def _handle_missing(self, df: pd.DataFrame, name: str) -> pd.DataFrame:
        """Forward-fill → backfill cho phần đầu chuỗi."""
        missing = df[PRICE_COLS].isnull().sum().sum() if all(c in df.columns for c in PRICE_COLS) else 0
        if missing:
            df[PRICE_COLS] = df[PRICE_COLS].ffill().bfill()
            logger.debug(f"[{name}] Forward-fill {missing} giá trị thiếu.")
        return df

    def _flag_outliers(self, df: pd.DataFrame, name: str) -> pd.DataFrame:
        """Đánh dấu ngày có biến động giá bất thường (>3 độ lệch chuẩn).

        KHÔNG xoá — chỉ đánh dấu để phân tích sau.
        Nguyên nhân thường gặp: tách cổ phiếu, trả cổ tức lớn, lỗi dữ liệu.
        """
        if "close" not in df.columns:
            return df
        returns = df["close"].pct_change()
        mean, std = returns.mean(), returns.std()
        if std == 0 or pd.isna(std):
            df["is_outlier"] = False
            return df
        df["is_outlier"] = (returns - mean).abs() > 3 * std
        n = int(df["is_outlier"].sum())
        if n:
            logger.debug(f"[{name}] Đánh dấu {n} outlier.")
        return df
