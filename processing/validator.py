import logging

import pandas as pd

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ["open", "high", "low", "close"]


class Validator:
    def validate(self, df: pd.DataFrame, name: str) -> bool:
        ok = True
        missing = [c for c in REQUIRED_COLUMNS if c in df.columns and df[c].isnull().any()]
        if missing:
            logger.warning(f"[{name}] NaN remaining in: {missing}")
            ok = False
        if df.index.duplicated().any():
            logger.warning(f"[{name}] Duplicate index entries remain.")
            ok = False
        if len(df) < 10:
            logger.warning(f"[{name}] Very few rows ({len(df)}) — check data source.")
            ok = False
        if ok:
            logger.info(f"[{name}] Validation passed. Shape: {df.shape}")
        return ok
