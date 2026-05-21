"""
FinAgent — AI-Powered Financial Data Agent
Usage:
    # Chạy toàn bộ pipeline (full market + macro)
    python main.py --all

    # Chạy từng bước
    python main.py --step collect          # Toàn sàn VN + 19 chỉ số macro
    python main.py --step collect --quick  # Chỉ 5 mã mẫu + macro (để test)
    python main.py --step process
    python main.py --step visualize
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


def run_collect(quick: bool = False) -> None:
    from collection.vn_stock_collector import VNStockCollector
    from collection.macro_collector import MacroCollector

    settings.ensure_dirs()

    if quick:
        # Chế độ test: chỉ lấy vài mã mẫu
        logger.info("=== CHẾ ĐỘ QUICK: chỉ tải mã mẫu ===")
        VNStockCollector().collect(symbols=settings.sample_tickers)
    else:
        # Chế độ đầy đủ: toàn bộ ~1535 mã VN
        logger.info("=== CHẾ ĐỘ FULL: tải toàn bộ cổ phiếu VN ===")
        VNStockCollector().collect()

    logger.info("=== Thu thập chỉ số macro ===")
    MacroCollector().collect()


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


def run_visualize() -> None:
    from visualization.trend_chart import plot_trend
    from visualization.heatmap import plot_heatmap
    from visualization.distribution import plot_distribution
    from visualization.rolling_stats import plot_rolling_stats
    import pandas as pd

    logger.info("Đang tạo biểu đồ...")
    frames = {}
    for f in settings.processed_data_dir.glob("*.csv"):
        try:
            df = pd.read_csv(f, index_col=0, parse_dates=True)
            frames[f.stem] = df
        except Exception:
            pass

    if frames:
        plot_trend(frames, settings.charts_dir)
        plot_heatmap(frames, settings.charts_dir)
        plot_distribution(frames, settings.charts_dir)
        plot_rolling_stats(frames, settings.charts_dir)
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
    parser.add_argument("--quick", action="store_true",
                        help="Chỉ dùng với --step collect: tải mã mẫu thay vì toàn sàn")
    args = parser.parse_args()

    if args.all:
        run_collect(quick=False)
        run_process()
        run_visualize()
        run_analyze()
    elif args.step == "collect":
        run_collect(quick=args.quick)
    elif args.step == "process":
        run_process()
    elif args.step == "visualize":
        run_visualize()
    elif args.step == "analyze":
        run_analyze()


if __name__ == "__main__":
    main()
