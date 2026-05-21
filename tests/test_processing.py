import pandas as pd
import numpy as np
import pytest

from processing.cleaner import Cleaner
from processing.feature_engineer import FeatureEngineer
from processing.validator import Validator


@pytest.fixture
def sample_df():
    dates = pd.date_range("2024-01-01", periods=60, freq="B")
    prices = np.random.lognormal(mean=0.0005, sigma=0.01, size=60).cumprod() * 100
    df = pd.DataFrame({
        "open": prices * 0.99,
        "high": prices * 1.01,
        "low": prices * 0.98,
        "close": prices,
        "volume": np.random.randint(1_000_000, 5_000_000, size=60),
    }, index=dates)
    return df


def test_cleaner_removes_duplicates(sample_df):
    df_dup = pd.concat([sample_df, sample_df.iloc[:5]])
    cleaner = Cleaner()
    # Write to temp file and clean
    import tempfile, os
    from pathlib import Path
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        df_dup.to_csv(f.name)
        cleaned = cleaner.clean(Path(f.name))
    os.unlink(f.name)
    assert len(cleaned) == len(sample_df)


def test_feature_engineer_adds_columns(sample_df):
    engineer = FeatureEngineer()
    result = engineer.engineer(sample_df)
    for col in ["daily_return", "ma_7", "ma_30", "volatility_30", "bb_upper", "bb_lower"]:
        assert col in result.columns, f"Missing column: {col}"


def test_validator_passes_clean_data(sample_df):
    engineer = FeatureEngineer()
    df = engineer.engineer(sample_df)
    validator = Validator()
    assert validator.validate(df, "test_asset") is True
