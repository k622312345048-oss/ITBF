"""Process raw news.csv into daily sentiment scores per keyword.

Dùng keyword-based sentiment (không cần thư viện NLP ngoài):
  - positive_score: đếm từ tích cực trong title + description
  - negative_score: đếm từ tiêu cực
  - sentiment: (pos - neg) / (pos + neg), range [-1, 1]
    +1 = toàn tích cực, -1 = toàn tiêu cực, 0 = trung lập

Output: DataFrame gồm [date, keyword, sentiment_mean, article_count]
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_POSITIVE = {
    "gain", "gains", "rise", "rises", "rose", "surge", "surges", "surged",
    "growth", "grow", "grew", "beat", "beats", "profit", "profits",
    "strong", "strength", "increase", "increased", "up", "high", "higher",
    "positive", "bullish", "rally", "rallied", "record", "outperform",
    "upgrade", "buy", "recover", "recovery", "recovered", "robust",
    "improve", "improved", "boost", "boosted", "advance", "advances",
}

_NEGATIVE = {
    "fall", "falls", "fell", "drop", "drops", "dropped", "loss", "losses",
    "decline", "declined", "crash", "crashed", "miss", "misses", "missed",
    "weak", "weakness", "decrease", "decreased", "down", "low", "lower",
    "negative", "bearish", "plunge", "plunged", "underperform", "downgrade",
    "sell", "risk", "risks", "concern", "concerns", "warning", "warnings",
    "disappoint", "disappointed", "disappointing", "slump", "slumped",
    "tumble", "tumbled", "sink", "sank", "worsen", "worsened",
}


def _sentiment_score(text: str) -> float:
    """Tính sentiment score từ một đoạn text. Range [-1, 1]."""
    if not isinstance(text, str) or not text.strip():
        return 0.0
    words = [w.strip(".,!?;:\"'()[]") for w in text.lower().split()]
    pos = sum(1 for w in words if w in _POSITIVE)
    neg = sum(1 for w in words if w in _NEGATIVE)
    total = pos + neg
    return (pos - neg) / total if total > 0 else 0.0


class NewsProcessor:

    def process(self, filepath: Path) -> pd.DataFrame:
        """Đọc news.csv thô, tính sentiment, trả về daily aggregation."""
        df = pd.read_csv(filepath)
        if df.empty:
            logger.warning(f"[news] File rỗng: {filepath.name}")
            return pd.DataFrame(columns=["date", "keyword", "sentiment_mean", "article_count"])

        original_len = len(df)

        # Chuẩn hoá ngày
        df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True)
        df = df.dropna(subset=["published_at"])
        df["date"] = df["published_at"].dt.normalize().dt.tz_localize(None)

        # Xóa bản ghi thiếu keyword hoặc title
        df = df.dropna(subset=["keyword", "title"])
        df["keyword"] = df["keyword"].str.upper()

        # Tính sentiment từ title + description
        combined_text = df["title"].fillna("") + " " + df["description"].fillna("")
        df["sentiment"] = combined_text.apply(_sentiment_score)

        # Aggregate theo ngày + keyword
        agg = (
            df.groupby(["date", "keyword"])
            .agg(
                sentiment_mean=("sentiment", "mean"),
                article_count=("sentiment", "count"),
            )
            .reset_index()
            .sort_values(["keyword", "date"])
            .reset_index(drop=True)
        )

        logger.info(
            f"[news] Xử lý xong: {original_len} bài → {len(agg)} bản ghi daily "
            f"({agg['keyword'].nunique()} mã, {agg['date'].nunique()} ngày)"
        )
        return agg
