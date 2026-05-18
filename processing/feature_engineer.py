import logging

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class FeatureEngineer:
    def engineer(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns:
            return df
        df = self._daily_returns(df)
        df = self._rolling_averages(df)
        df = self._volatility(df)
        df = self._bollinger_bands(df)
        logger.info("Feature engineering complete.")
        return df

    def _daily_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        df["daily_return"] = df["close"].pct_change()
        return df

    def _rolling_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        df["ma_7"] = df["close"].rolling(7).mean()
        df["ma_30"] = df["close"].rolling(30).mean()
        return df

    def _volatility(self, df: pd.DataFrame) -> pd.DataFrame:
        # Annualised rolling 30-day volatility
        df["volatility_30"] = df["daily_return"].rolling(30).std() * np.sqrt(252)
        return df

    def _bollinger_bands(self, df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        rolling = df["close"].rolling(window)
        df["bb_mid"] = rolling.mean()
        df["bb_upper"] = df["bb_mid"] + 2 * rolling.std()
        df["bb_lower"] = df["bb_mid"] - 2 * rolling.std()
        return df
