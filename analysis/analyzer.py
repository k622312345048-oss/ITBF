import logging
import time
from datetime import datetime
import pandas as pd

from analysis.llm_client import chat
from analysis.prompt_builder import build_summary_prompt, build_comparison_prompt
from config import settings

logger = logging.getLogger(__name__)

RATE_LIMIT_SLEEP = 2.5   # giây giữa mỗi LLM call (Groq free: 30 req/phút)


def _load_news_sentiment() -> pd.DataFrame | None:
    path = settings.processed_data_dir / "news_sentiment.csv"
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
        df["date"] = pd.to_datetime(df["date"])
        return df
    except Exception as e:
        logger.warning(f"Không thể load news_sentiment.csv: {e}")
        return None


def _select_top_stocks(frames: dict[str, pd.DataFrame], top_n: int) -> dict[str, pd.DataFrame]:
    """Chọn top N mã có nhiều phiên giao dịch nhất (= thanh khoản cao nhất)."""
    stock_frames = {k: v for k, v in frames.items()
                    if k.startswith("stock_") and "close" in v.columns}
    ranked = sorted(stock_frames.items(), key=lambda x: len(x[1]), reverse=True)
    selected = dict(ranked[:top_n])
    logger.info(f"Chọn top {top_n} mã: {[k.replace('stock_','') for k in selected]}")
    return selected


class Analyzer:
    def run(self, frames: dict[str, pd.DataFrame],
            top_n: int | None = None,
            force: bool = False) -> str:
        """Phân tích AI cho các mã cổ phiếu.

        Args:
            frames:  Dict {tên_mã: DataFrame}.
            top_n:   Chỉ phân tích top N mã thanh khoản cao nhất.
                     None = phân tích tất cả (chậm với 1500+ mã).
            force:   Phân tích lại dù đã có file riêng.
        """
        stock_frames = {k: v for k, v in frames.items()
                        if k.startswith("stock_") and "close" in v.columns}

        if top_n:
            stock_frames = _select_top_stocks(frames, top_n)

        news_df = _load_news_sentiment()
        settings.analysis_dir.mkdir(parents=True, exist_ok=True)

        total = len(stock_frames)
        logger.info(f"Bắt đầu phân tích {total} mã (sleep {RATE_LIMIT_SLEEP}s/call)")
        logger.info(f"Ước tính: ~{total * RATE_LIMIT_SLEEP / 60:.0f} phút")

        sections = [f"# FinAgent Analysis Report\n_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n"]
        sections.append("## 1. Asset Summaries\n")

        success, skipped, failed = 0, 0, []

        for i, (name, df) in enumerate(stock_frames.items(), start=1):
            ticker = name.replace("stock_", "").upper()

            # Skip-existing: kiểm tra file riêng của mã này
            stock_file = settings.analysis_dir / f"stock_{ticker}.md"
            if stock_file.exists() and not force:
                cached = stock_file.read_text(encoding="utf-8")
                sections.append(f"### {ticker}\n{cached}\n")
                skipped += 1
                if i % 50 == 0:
                    logger.info(f"[{i}/{total}] {success} OK, {skipped} cached, {len(failed)} lỗi")
                continue

            logger.info(f"[{i}/{total}] Phân tích {ticker}...")
            prompt = build_summary_prompt(name, df, news_df=news_df)
            try:
                response = chat(prompt)
                # Lưu file riêng để resume được
                stock_file.write_text(response, encoding="utf-8")
                sections.append(f"### {ticker}\n{response}\n")
                success += 1
            except Exception as e:
                logger.error(f"LLM call thất bại cho {ticker}: {e}")
                sections.append(f"### {ticker}\n_Analysis unavailable: {e}_\n")
                failed.append(ticker)

            if i % 50 == 0:
                logger.info(f"[{i}/{total}] {success} OK, {skipped} cached, {len(failed)} lỗi")

            time.sleep(RATE_LIMIT_SLEEP)

        # Comparative analysis — chỉ dùng top 20 để prompt không quá dài
        if len(stock_frames) >= 2:
            sections.append("## 2. Comparative Analysis\n")
            compare_frames = _select_top_stocks(stock_frames, min(20, len(stock_frames)))
            logger.info(f"Generating comparison cho {len(compare_frames)} mã...")
            try:
                prompt = build_comparison_prompt(compare_frames)
                response = chat(prompt)
                sections.append(response + "\n")
            except Exception as e:
                logger.error(f"Comparison LLM call thất bại: {e}")

        logger.info(f"=== HOÀN THÀNH PHÂN TÍCH ===")
        logger.info(f"  Thành công: {success} | Cache: {skipped} | Lỗi: {len(failed)}")

        return "\n".join(sections)
