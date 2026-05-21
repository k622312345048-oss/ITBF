"""Biểu đồ 3: Phân phối lợi nhuận hàng ngày (Daily Returns Distribution).

Histogram + đường KDE, so sánh với phân phối chuẩn.
Đường đỏ = mean, vùng xanh = ±1 độ lệch chuẩn.
"""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

logger = logging.getLogger(__name__)

# Màu cho từng mã trong lưới subplot
COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
          "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]


def plot_distribution(frames: dict[str, pd.DataFrame], output_dir: Path,
                      max_tickers: int = 6) -> None:
    """Vẽ lưới histogram + KDE của daily returns cho từng mã.

    Args:
        frames:      Dict {tên_mã: DataFrame}.
        output_dir:  Thư mục lưu ảnh.
        max_tickers: Số mã tối đa hiển thị (mặc định 6).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Lọc mã có đủ daily_return
    valid = {name: df for name, df in frames.items()
             if "daily_return" in df.columns
             and df["daily_return"].dropna().shape[0] >= 100}

    if not valid:
        logger.warning("Không có mã nào đủ dữ liệu để vẽ distribution.")
        return

    # Giới hạn số mã
    selected = dict(list(valid.items())[:max_tickers])
    n = len(selected)
    ncols = min(3, n)
    nrows = (n + ncols - 1) // ncols

    fig, axes = plt.subplots(nrows, ncols,
                             figsize=(6 * ncols, 5 * nrows),
                             squeeze=False)
    fig.patch.set_facecolor("#f8f9fa")
    fig.suptitle("Phân phối Lợi nhuận Hàng ngày (Daily Returns Distribution)",
                 fontsize=15, fontweight="bold", y=1.01)

    for idx, (name, df) in enumerate(selected.items()):
        row, col = divmod(idx, ncols)
        ax = axes[row][col]
        ax.set_facecolor("#ffffff")

        ticker  = name.replace("stock_", "").upper()
        returns = df["daily_return"].dropna()
        color   = COLORS[idx % len(COLORS)]

        # Histogram + KDE
        sns.histplot(returns, kde=True, ax=ax,
                     color=color, alpha=0.6, stat="density",
                     line_kws={"linewidth": 2})

        # Đường phân phối chuẩn tham chiếu
        x = np.linspace(returns.min(), returns.max(), 200)
        ax.plot(x, stats.norm.pdf(x, returns.mean(), returns.std()),
                color="black", linestyle=":", linewidth=1.5,
                label="Phân phối chuẩn")

        # Đường mean
        ax.axvline(returns.mean(), color="red", linewidth=1.5,
                   linestyle="--", label=f"Mean: {returns.mean()*100:.3f}%")

        # Vùng ±1 std
        ax.axvspan(returns.mean() - returns.std(),
                   returns.mean() + returns.std(),
                   alpha=0.08, color=color, label="±1 std")

        # Stats text
        skew = returns.skew()
        kurt = returns.kurtosis()
        vol  = returns.std() * np.sqrt(252)
        ax.text(0.97, 0.97,
                f"Std: {returns.std()*100:.2f}%\n"
                f"Vol/năm: {vol*100:.1f}%\n"
                f"Skew: {skew:.2f}\n"
                f"Kurt: {kurt:.2f}",
                transform=ax.transAxes, fontsize=8,
                va="top", ha="right",
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))

        ax.set_title(f"{ticker} ({len(returns):,} phiên)", fontsize=11, fontweight="bold")
        ax.set_xlabel("Lợi nhuận hàng ngày", fontsize=9)
        ax.set_ylabel("Mật độ xác suất", fontsize=9)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x*100:.1f}%"))
        ax.legend(fontsize=7, loc="upper left")
        ax.grid(axis="y", linestyle=":", alpha=0.4)

    # Ẩn subplot thừa
    for idx in range(n, nrows * ncols):
        row, col = divmod(idx, ncols)
        axes[row][col].set_visible(False)

    plt.tight_layout()
    out = output_dir / "returns_distribution.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Đã lưu distribution plot ({n} mã) → {out.name}")
