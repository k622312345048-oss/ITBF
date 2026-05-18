"""
FinAgent — AI-Powered Financial Data Agent
Usage:
    python main.py --all
    python main.py --step collect
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


def run_collect():
    from collection.stock_collector import StockCollector
    from collection.macro_collector import MacroCollector
    from collection.news_collector import NewsCollector

    logger.info("Starting data collection...")
    settings.ensure_dirs()

    StockCollector().collect(settings.stock_tickers, settings.default_period)
    MacroCollector().collect(settings.macro_symbols, settings.default_period)
    NewsCollector().collect(settings.stock_tickers[:3])
    logger.info("Data collection complete.")


def run_process():
    from processing.cleaner import Cleaner
    from processing.feature_engineer import FeatureEngineer
    from processing.validator import Validator

    logger.info("Starting data processing...")
    cleaner = Cleaner()
    engineer = FeatureEngineer()
    validator = Validator()

    for raw_file in settings.raw_data_dir.glob("*.csv"):
        df = cleaner.clean(raw_file)
        df = engineer.engineer(df)
        validator.validate(df, raw_file.stem)
        out = settings.processed_data_dir / raw_file.name
        df.to_csv(out)
        logger.info(f"Processed → {out.name}")

    logger.info("Data processing complete.")


def run_visualize():
    from visualization.trend_chart import plot_trend
    from visualization.heatmap import plot_heatmap
    from visualization.distribution import plot_distribution
    from visualization.rolling_stats import plot_rolling_stats

    logger.info("Generating visualizations...")
    import pandas as pd

    frames = {}
    for f in settings.processed_data_dir.glob("*.csv"):
        frames[f.stem] = pd.read_csv(f, index_col=0, parse_dates=True)

    if frames:
        plot_trend(frames, settings.charts_dir)
        plot_heatmap(frames, settings.charts_dir)
        plot_distribution(frames, settings.charts_dir)
        plot_rolling_stats(frames, settings.charts_dir)

    logger.info(f"Charts saved to {settings.charts_dir}")


def run_analyze():
    from analysis.analyzer import Analyzer

    logger.info("Running AI analysis...")
    import pandas as pd

    frames = {}
    for f in settings.processed_data_dir.glob("*.csv"):
        frames[f.stem] = pd.read_csv(f, index_col=0, parse_dates=True)

    analyzer = Analyzer()
    report = analyzer.run(frames)

    out = settings.analysis_dir / "report.md"
    out.write_text(report)
    logger.info(f"Analysis saved to {out}")


STEPS = {
    "collect": run_collect,
    "process": run_process,
    "visualize": run_visualize,
    "analyze": run_analyze,
}


def main():
    parser = argparse.ArgumentParser(description="FinAgent pipeline")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Run full pipeline")
    group.add_argument("--step", choices=STEPS.keys(), help="Run a single step")
    args = parser.parse_args()

    if args.all:
        for step_fn in STEPS.values():
            step_fn()
    else:
        STEPS[args.step]()


if __name__ == "__main__":
    main()
