import logging
from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

logger = logging.getLogger(__name__)


def plot_distribution(frames: dict[str, pd.DataFrame], output_dir: Path) -> None:
    fig, axes = plt.subplots(
        1, len(frames), figsize=(6 * len(frames), 5), squeeze=False
    )

    for ax, (name, df) in zip(axes[0], frames.items()):
        if "daily_return" not in df.columns:
            continue
        returns = df["daily_return"].dropna()
        sns.histplot(returns, kde=True, ax=ax, color="#1f77b4", stat="density")
        ax.axvline(returns.mean(), color="red", linestyle="--", label=f"Mean: {returns.mean():.4f}")
        ax.set_title(f"{name} — Daily Returns Distribution")
        ax.set_xlabel("Daily Return")
        ax.set_ylabel("Density")
        ax.legend()

    out = output_dir / "returns_distribution.png"
    fig.savefig(out, bbox_inches="tight", dpi=150)
    plt.close(fig)
    logger.info(f"Saved distribution plot → {out.name}")
