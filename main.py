"""
FinAgent — AI-Powered Financial Data Agent
Usage:
    # Chạy toàn bộ pipeline
    python main.py --all

    # Chạy từng bước
    python main.py --step collect
    python main.py --step process
    python main.py --step visualize                          # 10 mã mặc định
    python main.py --step visualize --tickers VNM,HPG,FPT   # Tự chọn mã
    python main.py --step analyze
"""

import argparse
import logging

from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("finagent")


def run_collect() -> None:
    from collection.vn_stock_collector import VNStockCollector
    from collection.macro_collector import MacroCollector
    from collection.news_collector import NewsCollector

    settings.ensure_dirs()

    logger.info(f"=== Thu thập {len(settings.stock_tickers)} cổ phiếu ===")
    VNStockCollector().collect(symbols=settings.stock_tickers)

    logger.info(f"=== Thu thập {len(settings.macro_symbols)} chỉ số macro ===")
    MacroCollector().collect(symbols=settings.macro_symbols)

    # Dùng keywords thị trường rộng — tickers VN không có coverage tiếng Anh
    news_keywords = [
        "Vietnam stock market",
        "VN-Index",
        "Vietnam economy",
        "FPT Vietnam",
        "Vinhomes",
        "Hoa Phat steel",
    ]
    logger.info(f"=== Thu thập news ({len(news_keywords)} keywords) ===")
    NewsCollector().collect(keywords=news_keywords)


def run_process() -> None:
    from processing.cleaner import Cleaner
    from processing.feature_engineer import FeatureEngineer
    from processing.validator import Validator
    from processing.news_processor import NewsProcessor

    logger.info("Bắt đầu xử lý dữ liệu...")
    cleaner   = Cleaner()
    engineer  = FeatureEngineer()
    validator = Validator()

    # Xử lý news.csv riêng (cấu trúc khác OHLCV)
    news_file = settings.raw_data_dir / "news.csv"
    if news_file.exists():
        try:
            news_df = NewsProcessor().process(news_file)
            out = settings.processed_data_dir / "news_sentiment.csv"
            news_df.to_csv(out, index=False)
            logger.info(f"News sentiment đã lưu → {out.name}")
        except Exception as e:
            logger.error(f"Lỗi xử lý news.csv: {e}")

    # Xử lý các file OHLCV (stock + macro), bỏ qua news.csv
    ohlcv_files = [f for f in settings.raw_data_dir.glob("*.csv") if f.name != "news.csv"]
    logger.info(f"Tìm thấy {len(ohlcv_files)} files OHLCV cần xử lý")

    for raw_file in ohlcv_files:
        try:
            df = cleaner.clean(raw_file)
            df = engineer.engineer(df)
            validator.validate(df, raw_file.stem)
            out = settings.processed_data_dir / raw_file.name
            df.to_csv(out)
        except Exception as e:
            logger.error(f"Lỗi xử lý {raw_file.name}: {e}")


def run_visualize(tickers: list[str] | None = None) -> None:
    from visualization.trend_chart import plot_trend
    from visualization.heatmap import plot_heatmap
    from visualization.distribution import plot_distribution
    from visualization.rolling_stats import plot_rolling_stats
    import pandas as pd

    logger.info("Đang tạo biểu đồ...")

    # Load tất cả processed files
    all_frames: dict[str, pd.DataFrame] = {}
    for f in settings.processed_data_dir.glob("*.csv"):
        try:
            all_frames[f.stem] = pd.read_csv(f, index_col=0, parse_dates=True)
        except Exception:
            pass

    if tickers:
        keys = [f"stock_{t.upper()}" for t in tickers]
        focus = {k: all_frames[k] for k in keys if k in all_frames}
        missing = [t.upper() for t in tickers if f"stock_{t.upper()}" not in all_frames]
        if missing:
            logger.warning(f"Không tìm thấy dữ liệu cho: {missing} — bỏ qua.")
    else:
        # Dùng danh sách từ config
        stock_keys = [f"stock_{t}" for t in settings.stock_tickers]
        focus = {k: all_frames[k] for k in stock_keys if k in all_frames}

    if not focus:
        logger.error("Không có dữ liệu để vẽ. Chạy --step process trước.")
        return

    logger.info(f"Vẽ biểu đồ cho: {[k.replace('stock_','') for k in focus.keys()]}")

    plot_trend(focus, settings.charts_dir)
    plot_heatmap(all_frames, settings.charts_dir)   # include macro cho heatmap
    plot_distribution(focus, settings.charts_dir)
    plot_rolling_stats(focus, settings.charts_dir)

    logger.info(f"Biểu đồ đã lưu tại {settings.charts_dir}")


def run_analyze() -> None:
    from analysis.analyzer import Analyzer
    import pandas as pd

    logger.info("Đang chạy phân tích AI...")
    frames = {}
    for f in settings.processed_data_dir.glob("*.csv"):
        try:
            df = pd.read_csv(f, index_col=0, parse_dates=True)
            frames[f.stem] = df
        except Exception:
            pass

    report = Analyzer().run(frames)
    out = settings.analysis_dir / "report.md"
    out.write_text(report, encoding="utf-8")
    logger.info(f"Báo cáo đã lưu tại {out}")


def main():
    parser = argparse.ArgumentParser(description="FinAgent pipeline")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all",  action="store_true", help="Chạy full pipeline")
    group.add_argument("--step", choices=["collect", "process", "visualize", "analyze"],
                       help="Chạy từng bước")
    parser.add_argument("--tickers", type=str, default=None,
                        help="Danh sách mã cách nhau bằng dấu phẩy, ví dụ: VNM,HPG,FPT")
    args = parser.parse_args()

    tickers = [t.strip() for t in args.tickers.split(",")] if args.tickers else None

    if args.all:
        run_collect()
        run_process()
        run_visualize(tickers)
        run_analyze()
    elif args.step == "collect":
        run_collect()
    elif args.step == "process":
        run_process()
    elif args.step == "visualize":
        run_visualize(tickers)
    elif args.step == "analyze":
        run_analyze()


if __name__ == "__main__":
    main()
