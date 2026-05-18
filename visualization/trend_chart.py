import logging
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import pandas as pd

logger = logging.getLogger(__name__)


def plot_trend(frames: dict[str, pd.DataFrame], output_dir: Path) -> None:
    for name, df in frames.items():
        if "close" not in df.columns:
            continue
        fig = plt.figure(figsize=(14, 7))
        gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1], hspace=0.05)

        ax1 = fig.add_subplot(gs[0])
        ax1.plot(df.index, df["close"], label="Close", linewidth=1.5, color="#1f77b4")
        if "ma_7" in df.columns:
            ax1.plot(df.index, df["ma_7"], label="MA 7d", linestyle="--", linewidth=1, color="orange")
        if "ma_30" in df.columns:
            ax1.plot(df.index, df["ma_30"], label="MA 30d", linestyle="--", linewidth=1, color="green")
        ax1.set_ylabel("Price")
        ax1.set_title(f"{name} — Price Trend")
        ax1.legend()
        ax1.set_xticklabels([])

        if "volume" in df.columns:
            ax2 = fig.add_subplot(gs[1], sharex=ax1)
            ax2.bar(df.index, df["volume"], color="#aec7e8", alpha=0.7)
            ax2.set_ylabel("Volume")
            ax2.set_xlabel("Date")

        out = output_dir / f"trend_{name}.png"
        fig.savefig(out, bbox_inches="tight", dpi=150)
        plt.close(fig)
        logger.info(f"Saved trend chart → {out.name}")
