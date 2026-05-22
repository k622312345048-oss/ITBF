"""Kiểm tra chất lượng dữ liệu sau khi xử lý.

Các kiểm tra:
1. Đủ cột bắt buộc (open, high, low, close)
2. Không còn NaN trong giá
3. Không còn ngày trùng
4. Đủ số phiên tối thiểu để tính toán có ý nghĩa
5. Giá high >= low (kiểm tra tính nhất quán OHLC)
6. Các feature đã được tính đủ
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)

REQUIRED_PRICE_COLS  = ["open", "high", "low", "close"]
REQUIRED_FEATURE_COLS = ["daily_return", "ma_7", "ma_30", "volatility_30",
                          "bb_upper", "bb_lower"]
MIN_ROWS = 30   # Tối thiểu để Bollinger Bands có ý nghĩa


class Validator:

    def validate(self, df: pd.DataFrame, name: str) -> bool:
        """Chạy toàn bộ kiểm tra. Trả về True nếu pass hết."""
        checks = [
            self._check_required_columns(df, name),
            self._check_no_nan_prices(df, name),
            self._check_no_duplicate_index(df, name),
            self._check_min_rows(df, name),
            self._check_ohlc_consistency(df, name),
            self._check_features_present(df, name),
        ]
        passed = all(checks)
        if passed:
            logger.debug(f"[{name}] ✓ {len(df)} rows "
                         f"({df.index[0].date()} → {df.index[-1].date()})")
        return passed

    # ──────────────────────────────────────────────

    def _check_required_columns(self, df: pd.DataFrame, name: str) -> bool:
        missing = [c for c in REQUIRED_PRICE_COLS if c not in df.columns]
        if missing:
            logger.error(f"[{name}] Thiếu cột: {missing}")
            return False
        return True

    def _check_no_nan_prices(self, df: pd.DataFrame, name: str) -> bool:
        cols = [c for c in REQUIRED_PRICE_COLS if c in df.columns]
        nan_count = df[cols].isnull().sum().sum()
        if nan_count:
            logger.warning(f"[{name}] Còn {nan_count} NaN trong giá sau khi clean.")
            return False
        return True

    def _check_no_duplicate_index(self, df: pd.DataFrame, name: str) -> bool:
        dupes = df.index.duplicated().sum()
        if dupes:
            logger.warning(f"[{name}] Còn {dupes} ngày trùng lặp.")
            return False
        return True

    def _check_min_rows(self, df: pd.DataFrame, name: str) -> bool:
        if len(df) < MIN_ROWS:
            logger.warning(f"[{name}] Chỉ có {len(df)} rows (tối thiểu {MIN_ROWS}).")
            return False
        return True

    def _check_ohlc_consistency(self, df: pd.DataFrame, name: str) -> bool:
        if not all(c in df.columns for c in ["high", "low"]):
            return True
        bad = (df["high"] < df["low"]).sum()
        if bad:
            logger.warning(f"[{name}] {bad} ngày có high < low (lỗi dữ liệu).")
            return False
        return True

    def _check_features_present(self, df: pd.DataFrame, name: str) -> bool:
        missing = [c for c in REQUIRED_FEATURE_COLS if c not in df.columns]
        if missing:
            logger.warning(f"[{name}] Thiếu feature: {missing}")
            return False
        return True
