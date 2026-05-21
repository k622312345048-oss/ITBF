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

    settings.ensure_dirs()

    logger.info(f"=== Thu thập {len(settings.stock_tickers)} cổ phiếu ===")
    VNStockCollector().collect(symbols=settings.stock_tickers)

    logger.info(f"=== Thu thập {len(settings.macro_symbols)} chỉ số macro ===")
    MacroCollector().collect(symbols=settings.macro_symbols)


def run_process() -> None:
    from processing.cleaner import Cleaner
    from processing.feature_engineer import FeatureEngineer
    from processing.validator import Validator

    logger.info("Bắt đầu xử lý dữ liệu...")
    cleaner   = Cleaner()
    engineer  = FeatureEngineer()
    validator = Validator()

    csv_files = list(settings.raw_data_dir.glob("*.csv"))
    logger.info(f"Tìm thấy {len(csv_files)} files cần xử lý")

    for raw_file in csv_files:
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

    # Nếu người dùng truyền --tickers thì dùng danh sách đó
    # Nếu không thì dùng blue-chip mặc định
    default_priority = ["stock_VNM", "stock_HPG", "stock_FPT",
                        "stock_VIC", "stock_ACB", "stock_MWG",
                        "stock_VCB", "stock_TCB", "stock_BID", "stock_CTG"]

    # Load tất cả processed files
    all_frames: dict[str, pd.DataFrame] = {}
    for f in settings.processed_data_dir.glob("*.csv"):
        try:
            all_frames[f.stem] = pd.read_csv(f, index_col=0, parse_dates=True)
        except Exception:
            pass

    if tickers:
        # Người dùng chỉ định mã cụ thể
        keys = [f"stock_{t.upper()}" for t in tickers]
        focus = {k: all_frames[k] for k in keys if k in all_frames}
        missing = [t.upper() for t in tickers if f"stock_{t.upper()}" not in all_frames]
        if missing:
            logger.warning(f"Không tìm thấy dữ liệu cho: {missing} — bỏ qua.")
    else:
        # Dùng blue-chip mặc định
        focus = {k: all_frames[k] for k in default_priority if k in all_frames}
        if not focus:
            focus = dict(list(all_frames.items())[:10])

    if not focus:
        logger.error("Không có dữ liệu để vẽ. Chạy --step process trước.")
        return

    logger.info(f"Vẽ biểu đồ cho: {[k.replace('stock_','') for k in focus.keys()]}")

    plot_trend(focus, settings.charts_dir)
    plot_heatmap(focus, settings.charts_dir)
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
