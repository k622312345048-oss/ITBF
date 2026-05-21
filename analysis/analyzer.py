import logging
from datetime import datetime

import pandas as pd

from analysis.llm_client import chat
from analysis.prompt_builder import build_summary_prompt, build_comparison_prompt
from config import settings

logger = logging.getLogger(__name__)


def _load_news_sentiment() -> pd.DataFrame | None:
    """Load news_sentiment.csv nếu có, trả về None nếu không tồn tại."""
    path = settings.processed_data_dir / "news_sentiment.csv"
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
        df["date"] = pd.to_datetime(df["date"])
        logger.info(f"Loaded news sentiment: {len(df)} records")
        return df
    except Exception as e:
        logger.warning(f"Không thể load news_sentiment.csv: {e}")
        return None


class Analyzer:
    def run(self, frames: dict[str, pd.DataFrame]) -> str:
        # Chỉ phân tích stock files, bỏ qua macro và news
        stock_frames = {k: v for k, v in frames.items()
                        if k.startswith("stock_") and "close" in v.columns}

        news_df = _load_news_sentiment()

        sections = [f"# FinAgent Analysis Report\n_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n"]

        # Per-stock summaries
        sections.append("## 1. Asset Summaries\n")
        for name, df in stock_frames.items():
            ticker = name.replace("stock_", "").upper()
            logger.info(f"Generating summary for {ticker}...")
            prompt = build_summary_prompt(name, df, news_df=news_df)
            try:
                response = chat(prompt)
                sections.append(f"### {ticker}\n{response}\n")
            except Exception as e:
                logger.error(f"LLM call failed for {ticker}: {e}")
                sections.append(f"### {ticker}\n_Analysis unavailable: {e}_\n")

        # Cross-stock comparison
        if len(stock_frames) >= 2:
            sections.append("## 2. Comparative Analysis\n")
            logger.info("Generating cross-stock comparison...")
            try:
                prompt = build_comparison_prompt(stock_frames)
                response = chat(prompt)
                sections.append(response + "\n")
            except Exception as e:
                logger.error(f"Comparison LLM call failed: {e}")

        return "\n".join(sections)
