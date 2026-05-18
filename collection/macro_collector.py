import logging

import yfinance as yf

from config import settings
from collection.base_collector import BaseCollector

logger = logging.getLogger(__name__)


class MacroCollector(BaseCollector):
    """Collect macro indicators (commodities, FX) via yfinance."""

    def collect(self, symbols: list[str], period: str = "6mo") -> None:
        for symbol in symbols:
            logger.info(f"Fetching macro: {symbol}")
            df = self._fetch_with_retry(self._download, symbol, period)
            if df.empty:
                logger.warning(f"No data for {symbol}")
                continue
            safe_name = symbol.replace("=", "_").replace("/", "_")
            out = settings.raw_data_dir / f"macro_{safe_name}.csv"
            df.to_csv(out)
            logger.info(f"Saved {len(df)} rows → {out.name}")

    def _download(self, symbol: str, period: str):
        df = yf.download(symbol, period=period, auto_adjust=True, progress=False)
        df.columns = [c.lower() for c in df.columns]
        df.index.name = "date"
        return df
