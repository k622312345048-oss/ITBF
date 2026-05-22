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


def run_collect_market() -> None:
    from collection.vn_stock_collector import VNStockCollector, get_all_market_tickers

    settings.ensure_dirs()
    tickers = get_all_market_tickers()
    logger.info(f"=== Thu thập toàn thị trường: {len(tickers)} mã (HOSE + HNX + UPCoM) ===")
    logger.info(f"Ước tính thời gian: ~{len(tickers) * 4.5 / 60:.0f} phút")
    logger.info("(Bỏ qua mã đã có file, chạy lại sẽ tiếp tục từ điểm dừng)")
    VNStockCollector().collect(symbols=tickers)


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


def run_process(force: bool = False) -> None:
    from processing.cleaner import Cleaner
    from processing.feature_engineer import FeatureEngineer
    from processing.validator import Validator
    from processing.news_processor import NewsProcessor

    settings.ensure_dirs()
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

    # Xử lý tất cả file OHLCV trong raw/ (stock + macro), bỏ qua news.csv
    ohlcv_files = sorted(
        f for f in settings.raw_data_dir.glob("*.csv") if f.name != "news.csv"
    )
    total = len(ohlcv_files)
    logger.info(f"=== Xử lý {total} files OHLCV ===")

    success, skipped, failed = 0, 0, []
    REPORT_EVERY = 50

    for i, raw_file in enumerate(ohlcv_files, start=1):
        out = settings.processed_data_dir / raw_file.name

        # Bỏ qua nếu đã xử lý (trừ khi force=True)
        if out.exists() and not force:
            skipped += 1
            if i % REPORT_EVERY == 0:
                logger.info(f"[{i}/{total}] {success} OK, {skipped} bỏ qua, {len(failed)} lỗi")
            continue

        try:
            df = cleaner.clean(raw_file)
            df = engineer.engineer(df)
            validator.validate(df, raw_file.stem)
            df.to_csv(out)
            success += 1
        except Exception as e:
            failed.append(raw_file.name)
            logger.error(f"[{i}/{total}] Lỗi {raw_file.name}: {e}")

        if i % REPORT_EVERY == 0 or i == total:
            pct = i / total * 100
            logger.info(f"[{i}/{total} | {pct:.0f}%] {success} OK, {skipped} bỏ qua, {len(failed)} lỗi")

    logger.info("=== HOÀN THÀNH XỬ LÝ ===")
    logger.info(f"  Thành công : {success}")
    logger.info(f"  Bỏ qua    : {skipped} (đã có processed)")
    logger.info(f"  Thất bại  : {len(failed)}")
    if failed:
        logger.warning(f"  Mã lỗi: {failed[:20]}")


def run_process_watch(poll_seconds: int = 15) -> None:
    """Chạy liên tục: phát hiện file mới trong raw/ và process ngay.
    Dùng song song với collect-market. Ctrl+C để dừng.
    """
    import time
    from processing.cleaner import Cleaner
    from processing.feature_engineer import FeatureEngineer
    from processing.validator import Validator

    settings.ensure_dirs()
    cleaner  = Cleaner()
    engineer = FeatureEngineer()
    validator = Validator()

    done_total = 0
    logger.info(f"=== Process-watch: quét mỗi {poll_seconds}s (Ctrl+C để dừng) ===")

    try:
        while True:
            pending = [
                f for f in sorted(settings.raw_data_dir.glob("stock_*.csv"))
                if not (settings.processed_data_dir / f.name).exists()
            ]

            if pending:
                logger.info(f"Phát hiện {len(pending)} file chưa xử lý — đang process...")
                batch_ok, batch_fail = 0, 0
                for raw_file in pending:
                    out = settings.processed_data_dir / raw_file.name
                    try:
                        df = cleaner.clean(raw_file)
                        df = engineer.engineer(df)
                        validator.validate(df, raw_file.stem)
                        df.to_csv(out)
                        batch_ok += 1
                    except Exception as e:
                        batch_fail += 1
                        logger.error(f"Lỗi {raw_file.name}: {e}")
                done_total += batch_ok
                logger.info(f"Batch xong: {batch_ok} OK, {batch_fail} lỗi | Tổng đã xử lý: {done_total}")

            time.sleep(poll_seconds)

    except KeyboardInterrupt:
        logger.info(f"Watch dừng. Tổng đã xử lý: {done_total} mã.")


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
    plot_heatmap(all_frames, settings.charts_dir)
    plot_distribution(focus, settings.charts_dir)
    plot_rolling_stats(focus, settings.charts_dir)

    logger.info(f"Biểu đồ đã lưu tại {settings.charts_dir}")


def run_analyze(top_n: int | None = None, force: bool = False) -> None:
    from analysis.analyzer import Analyzer
    import pandas as pd

    logger.info("Đang chạy phân tích AI...")
    frames = {}
    for f in settings.processed_data_dir.glob("*.csv"):
        try:
            frames[f.stem] = pd.read_csv(f, index_col=0, parse_dates=True)
        except Exception:
            pass

    report = Analyzer().run(frames, top_n=top_n, force=force)
    out = settings.analysis_dir / "report.md"
    out.write_text(report, encoding="utf-8")
    logger.info(f"Báo cáo đã lưu tại {out}")


def main():
    parser = argparse.ArgumentParser(description="FinAgent pipeline")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all",  action="store_true", help="Chạy full pipeline")
    group.add_argument("--step", choices=["collect", "collect-market", "process", "process-watch", "visualize", "analyze"],
                       help="Chạy từng bước (collect-market = tải toàn bộ HOSE+HNX+UPCoM, process-watch = xử lý liên tục song song với collect)")
    parser.add_argument("--tickers", type=str, default=None,
                        help="Danh sách mã cách nhau bằng dấu phẩy, ví dụ: VNM,HPG,FPT")
    parser.add_argument("--force-process", action="store_true",
                        help="Xử lý lại tất cả, kể cả file đã có trong processed/")
    parser.add_argument("--top", type=int, default=None,
                        help="Chỉ analyze top N mã thanh khoản cao nhất (mặc định: tất cả)")
    parser.add_argument("--force-analyze", action="store_true",
                        help="Phân tích lại dù đã có cache")
    args = parser.parse_args()

    tickers = [t.strip() for t in args.tickers.split(",")] if args.tickers else None

    force = args.force_process

    if args.all:
        run_collect()
        run_process(force=force)
        run_visualize(tickers)
        run_analyze()
    elif args.step == "collect":
        run_collect()
    elif args.step == "collect-market":
        run_collect_market()
    elif args.step == "process":
        run_process(force=force)
    elif args.step == "process-watch":
        run_process_watch()
    elif args.step == "visualize":
        run_visualize(tickers)
    elif args.step == "analyze":
        run_analyze(top_n=args.top, force=args.force_analyze)


if __name__ == "__main__":
    main()
