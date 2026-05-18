import logging
from pathlib import Path

import yfinance as yf

from config import settings
from collection.base_collector import BaseCollector

logger = logging.getLogger(__name__)


class StockCollector(BaseCollector):
    """Collect OHLCV stock data via yfinance."""

    def collect(self, tickers: list[str], period: str = "6mo") -> None:
        for ticker in tickers:
            logger.info(f"Fetching stock: {ticker}")
            df = self._fetch_with_retry(self._download, ticker, period)
            if df.empty:
                logger.warning(f"No data returned for {ticker}")
                continue
            out = settings.raw_data_dir / f"{ticker.replace('=', '_')}.csv"
            df.to_csv(out)
            logger.info(f"Saved {len(df)} rows → {out.name}")

    def _download(self, ticker: str, period: str):
        df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        df.columns = [c.lower() for c in df.columns]
        df.index.name = "date"
        return df
