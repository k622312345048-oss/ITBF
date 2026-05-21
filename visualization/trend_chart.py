"""Biểu đồ 1: Xu hướng giá + khối lượng giao dịch (Price Trend + Volume).

Hiển thị đường giá đóng cửa cùng MA 7 và MA 30 ngày (panel trên),
và khối lượng giao dịch theo ngày (panel dưới).
"""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
import pandas as pd

logger = logging.getLogger(__name__)

# Màu sắc nhất quán cho toàn bộ module visualization
PALETTE = {
    "price":  "#1f77b4",
    "ma7":    "#ff7f0e",
    "ma30":   "#2ca02c",
    "volume": "#aec7e8",
}


def plot_trend(frames: dict[str, pd.DataFrame], output_dir: Path,
               lookback_years: int = 2) -> None:
    """Vẽ biểu đồ xu hướng giá + volume cho từng mã trong frames.

    Args:
        frames:         Dict {tên_mã: DataFrame đã xử lý}.
        output_dir:     Thư mục lưu ảnh.
        lookback_years: Chỉ hiển thị N năm gần nhất (mặc định 2).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, df in frames.items():
        if "close" not in df.columns or df.empty:
            continue

        # Chỉ lấy dữ liệu trong N năm gần nhất
        cutoff = df.index.max() - pd.DateOffset(years=lookback_years)
        df = df[df.index >= cutoff].copy()
        if len(df) < 10:
            continue

        ticker = name.replace("stock_", "").upper()

        fig = plt.figure(figsize=(14, 8))
        fig.patch.set_facecolor("#f8f9fa")
        gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1], hspace=0.08)

        # ── Panel trên: Giá + MA ─────────────────────────────
        ax1 = fig.add_subplot(gs[0])
        ax1.set_facecolor("#ffffff")
        ax1.plot(df.index, df["close"],
                 color=PALETTE["price"], linewidth=1.8, label="Giá đóng cửa", zorder=3)

        if "ma_7" in df.columns:
            ax1.plot(df.index, df["ma_7"],
                     color=PALETTE["ma7"], linewidth=1.2,
                     linestyle="--", label="MA 7 ngày", alpha=0.9)
        if "ma_30" in df.columns:
            ax1.plot(df.index, df["ma_30"],
                     color=PALETTE["ma30"], linewidth=1.2,
                     linestyle="--", label="MA 30 ngày", alpha=0.9)

        ax1.set_title(f"{ticker} — Xu hướng giá & Khối lượng giao dịch "
                      f"({lookback_years} năm gần nhất)",
                      fontsize=14, fontweight="bold", pad=12)
        ax1.set_ylabel("Giá (nghìn VNĐ)", fontsize=11)
        ax1.legend(loc="upper left", fontsize=9, framealpha=0.8)
        ax1.grid(axis="y", linestyle=":", alpha=0.5)
        ax1.tick_params(labelbottom=False)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))

        # ── Panel dưới: Volume ───────────────────────────────
        if "volume" in df.columns:
            ax2 = fig.add_subplot(gs[1], sharex=ax1)
            ax2.set_facecolor("#ffffff")
            ax2.bar(df.index, df["volume"],
                    color=PALETTE["volume"], alpha=0.8, width=1.5)
            ax2.set_ylabel("KL (CP)", fontsize=10)
            ax2.set_xlabel("Ngày", fontsize=11)
            ax2.yaxis.set_major_formatter(
                plt.FuncFormatter(lambda x, _: f"{x/1e6:.1f}M" if x >= 1e6 else f"{x/1e3:.0f}K"))
            ax2.grid(axis="y", linestyle=":", alpha=0.4)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
            ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha="right")

        plt.tight_layout()
        out = output_dir / f"trend_{ticker}.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"Đã lưu trend chart → {out.name}")
