import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np


def _mock_ohlcv(n=30):
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.DataFrame({
        "open": np.random.uniform(90, 110, n),
        "high": np.random.uniform(100, 120, n),
        "low": np.random.uniform(80, 100, n),
        "close": np.random.uniform(90, 110, n),
        "volume": np.random.randint(1_000_000, 5_000_000, n),
    }, index=dates)


@patch("yfinance.download")
def test_stock_collector_saves_csv(mock_download, tmp_path, monkeypatch):
    mock_download.return_value = _mock_ohlcv()

    import config
    monkeypatch.setattr(config.settings, "raw_data_dir", tmp_path)

    from collection.stock_collector import StockCollector
    StockCollector().collect(["AAPL"], period="1mo")

    saved = list(tmp_path.glob("*.csv"))
    assert len(saved) == 1


@patch("yfinance.download")
def test_stock_collector_skips_empty(mock_download, tmp_path, monkeypatch):
    mock_download.return_value = pd.DataFrame()

    import config
    monkeypatch.setattr(config.settings, "raw_data_dir", tmp_path)

    from collection.stock_collector import StockCollector
    StockCollector().collect(["INVALID"], period="1mo")

    saved = list(tmp_path.glob("*.csv"))
    assert len(saved) == 0
