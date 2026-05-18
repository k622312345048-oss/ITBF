import logging
from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

logger = logging.getLogger(__name__)


def plot_heatmap(frames: dict[str, pd.DataFrame], output_dir: Path) -> None:
    close_prices = {}
    for name, df in frames.items():
        if "close" in df.columns:
            close_prices[name] = df["close"]

    if len(close_prices) < 2:
        logger.warning("Need at least 2 assets for correlation heatmap.")
        return

    combined = pd.DataFrame(close_prices).pct_change().dropna()
    corr = combined.corr()

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(
        corr,
        annot=True,
        fmt=".2f",
        cmap="RdYlGn",
        vmin=-1, vmax=1,
        square=True,
        ax=ax,
    )
    ax.set_title("Return Correlation Heatmap")

    out = output_dir / "correlation_heatmap.png"
    fig.savefig(out, bbox_inches="tight", dpi=150)
    plt.close(fig)
    logger.info(f"Saved heatmap → {out.name}")
