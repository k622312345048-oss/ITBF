"""Biểu đồ 2: Correlation Heatmap — tương quan lợi nhuận giữa các cổ phiếu.

Màu xanh = tương quan dương (cùng chiều).
Màu đỏ  = tương quan âm (ngược chiều).
"""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

logger = logging.getLogger(__name__)


def plot_heatmap(frames: dict[str, pd.DataFrame], output_dir: Path,
                 min_overlap: int = 252) -> None:
    """Vẽ correlation heatmap của daily returns.

    Args:
        frames:       Dict {tên_mã: DataFrame}.
        output_dir:   Thư mục lưu ảnh.
        min_overlap:  Số ngày chung tối thiểu để đưa mã vào heatmap.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Thu thập daily_return của từng mã
    returns = {}
    for name, df in frames.items():
        col = "daily_return" if "daily_return" in df.columns else None
        if col is None and "close" in df.columns:
            df = df.copy()
            df["daily_return"] = df["close"].pct_change()
            col = "daily_return"
        if col:
            ticker = name.replace("stock_", "").replace("macro_", "").upper()
            returns[ticker] = df[col]

    if len(returns) < 2:
        logger.warning("Cần ít nhất 2 mã để vẽ heatmap.")
        return

    # Ghép thành một DataFrame, bỏ mã có quá ít dữ liệu chung
    combined = pd.DataFrame(returns)
    valid_cols = [c for c in combined.columns
                  if combined[c].dropna().shape[0] >= min_overlap]
    combined = combined[valid_cols].dropna(how="all")

    if len(valid_cols) < 2:
        logger.warning("Không đủ mã có dữ liệu chung để vẽ heatmap.")
        return

    corr = combined.corr(min_periods=min_overlap // 2)

    n = len(corr)
    fig_size = max(10, n * 0.7)
    fig, ax = plt.subplots(figsize=(fig_size, fig_size * 0.85))
    fig.patch.set_facecolor("#f8f9fa")

    # Ẩn annotation nếu quá nhiều mã (khó đọc)
    annot = n <= 20
    fmt   = ".2f" if annot else ""

    sns.heatmap(
        corr,
        annot=annot,
        fmt=fmt,
        cmap="RdYlGn",
        vmin=-1, vmax=1,
        square=True,
        linewidths=0.5,
        linecolor="#dddddd",
        cbar_kws={"label": "Hệ số tương quan Pearson", "shrink": 0.8},
        ax=ax,
    )

    ax.set_title(
        f"Ma trận tương quan lợi nhuận hàng ngày — {n} mã\n"
        f"(Xanh = cùng chiều, Đỏ = ngược chiều)",
        fontsize=13, fontweight="bold", pad=15,
    )
    ax.tick_params(axis="x", rotation=45, labelsize=9)
    ax.tick_params(axis="y", rotation=0,  labelsize=9)

    plt.tight_layout()
    out = output_dir / "correlation_heatmap.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Đã lưu correlation heatmap ({n} mã) → {out.name}")
