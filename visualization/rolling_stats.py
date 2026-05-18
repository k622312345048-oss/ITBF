import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

logger = logging.getLogger(__name__)


def plot_rolling_stats(frames: dict[str, pd.DataFrame], output_dir: Path) -> None:
    for name, df in frames.items():
        if not all(c in df.columns for c in ["close", "bb_upper", "bb_lower", "bb_mid"]):
            continue
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.plot(df.index, df["close"], label="Close", linewidth=1.5, color="#1f77b4")
        ax.plot(df.index, df["bb_mid"], label="BB Mid (20d MA)", linestyle="--", color="orange")
        ax.plot(df.index, df["bb_upper"], label="BB Upper", linestyle=":", color="red")
        ax.plot(df.index, df["bb_lower"], label="BB Lower", linestyle=":", color="green")
        ax.fill_between(df.index, df["bb_lower"], df["bb_upper"], alpha=0.1, color="grey")
        ax.set_title(f"{name} — Bollinger Bands")
        ax.set_xlabel("Date")
        ax.set_ylabel("Price")
        ax.legend()

        out = output_dir / f"rolling_stats_{name}.png"
        fig.savefig(out, bbox_inches="tight", dpi=150)
        plt.close(fig)
        logger.info(f"Saved rolling stats chart → {out.name}")
