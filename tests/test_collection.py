import pandas as pd
import numpy as np
import pytest
from unittest.mock import patch


def _mock_ohlcv(n=30):
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.DataFrame({
        "open":   np.random.uniform(90, 110, n),
        "high":   np.random.uniform(100, 120, n),
        "low":    np.random.uniform(80, 100, n),
        "close":  np.random.uniform(90, 110, n),
        "volume": np.random.randint(1_000_000, 5_000_000, n),
    }, index=dates)


@patch("yfinance.download")
def test_macro_collector_saves_csv(mock_download, tmp_path, monkeypatch):
    mock_df = _mock_ohlcv()
    mock_download.return_value = mock_df

    import config
    monkeypatch.setattr(config.settings, "raw_data_dir", tmp_path)

    from collection.macro_collector import MacroCollector
    MacroCollector().collect(symbols=["GC=F"])

    saved = list(tmp_path.glob("macro_*.csv"))
    assert len(saved) == 1


@patch("yfinance.download")
def test_macro_collector_skips_empty(mock_download, tmp_path, monkeypatch):
    mock_download.return_value = pd.DataFrame()

    import config
    monkeypatch.setattr(config.settings, "raw_data_dir", tmp_path)

    from collection.macro_collector import MacroCollector
    MacroCollector().collect(symbols=["INVALID=X"])

    saved = list(tmp_path.glob("macro_*.csv"))
    assert len(saved) == 0


def test_macro_collector_skips_existing(tmp_path, monkeypatch):
    import config
    monkeypatch.setattr(config.settings, "raw_data_dir", tmp_path)

    # Tạo file sẵn
    existing = tmp_path / "macro_GC_F.csv"
    existing.write_text("date,close\n2024-01-01,1900\n")

    from collection.macro_collector import MacroCollector
    with patch("yfinance.download") as mock_dl:
        MacroCollector().collect(symbols=["GC=F"], force_reload=False)
        mock_dl.assert_not_called()
