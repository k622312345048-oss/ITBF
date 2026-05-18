import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class Cleaner:
    def clean(self, filepath: Path) -> pd.DataFrame:
        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        df = self._normalize_types(df)
        df = self._remove_duplicates(df)
        df = self._handle_missing(df)
        df = self._flag_outliers(df)
        return df

    def _normalize_types(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        before = len(df)
        df = df[~df.index.duplicated(keep="first")]
        removed = before - len(df)
        if removed:
            logger.info(f"Removed {removed} duplicate rows.")
        return df

    def _handle_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        missing = df.isnull().sum().sum()
        if missing:
            logger.info(f"Forward-filling {missing} missing values.")
            df = df.ffill().bfill()
        return df

    def _flag_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns:
            return df
        # Flag daily returns beyond 3 std as potential outliers
        returns = df["close"].pct_change()
        mean, std = returns.mean(), returns.std()
        df["is_outlier"] = (returns - mean).abs() > 3 * std
        n = df["is_outlier"].sum()
        if n:
            logger.info(f"Flagged {n} outlier rows.")
        return df
