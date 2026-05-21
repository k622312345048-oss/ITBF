"""Biểu đồ 4: Rolling Statistics — Bollinger Bands + MA.

Hiển thị giá đóng cửa cùng Bollinger Bands 20 ngày.
Vùng xanh giữa 2 dải BB = "vùng bình thường".
Giá chạm BB Upper → có thể quá mua.
Giá chạm BB Lower → có thể quá bán.
"""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

logger = logging.getLogger(__name__)


def plot_rolling_stats(frames: dict[str, pd.DataFrame], output_dir: Path,
                       lookback_years: int = 2) -> None:
    """Vẽ Bollinger Bands cho từng mã trong frames.

    Args:
        frames:         Dict {tên_mã: DataFrame đã xử lý}.
        output_dir:     Thư mục lưu ảnh.
        lookback_years: Số năm gần nhất hiển thị.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    required = ["close", "bb_upper", "bb_lower", "bb_mid"]

    for name, df in frames.items():
        if not all(c in df.columns for c in required) or df.empty:
            continue

        # Chỉ lấy N năm gần nhất
        cutoff = df.index.max() - pd.DateOffset(years=lookback_years)
        df = df[df.index >= cutoff].copy()
        if len(df) < 20:
            continue

        ticker = name.replace("stock_", "").upper()

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9),
                                        gridspec_kw={"height_ratios": [3, 1],
                                                     "hspace": 0.08})
        fig.patch.set_facecolor("#f8f9fa")

        # ── Panel trên: Giá + Bollinger Bands ───────────────
        ax1.set_facecolor("#ffffff")

        # Vùng giữa 2 dải BB
        ax1.fill_between(df.index, df["bb_lower"], df["bb_upper"],
                         alpha=0.12, color="#1f77b4", label="_nolegend_")

        ax1.plot(df.index, df["bb_upper"],
                 color="#d62728", linewidth=1.0, linestyle="--", label="BB Upper (+2σ)")
        ax1.plot(df.index, df["bb_mid"],
                 color="#ff7f0e", linewidth=1.2, linestyle="--", label="BB Mid (MA 20)")
        ax1.plot(df.index, df["bb_lower"],
                 color="#2ca02c", linewidth=1.0, linestyle="--", label="BB Lower (−2σ)")
        ax1.plot(df.index, df["close"],
                 color="#1f77b4", linewidth=1.8, label="Giá đóng cửa", zorder=5)

        # Đánh dấu các điểm giá chạm/phá dải BB
        touch_upper = df["close"] >= df["bb_upper"]
        touch_lower = df["close"] <= df["bb_lower"]
        if touch_upper.any():
            ax1.scatter(df.index[touch_upper], df["close"][touch_upper],
                        color="#d62728", s=20, zorder=6, alpha=0.7,
                        label=f"Chạm BB Upper ({touch_upper.sum()} phiên)")
        if touch_lower.any():
            ax1.scatter(df.index[touch_lower], df["close"][touch_lower],
                        color="#2ca02c", s=20, zorder=6, alpha=0.7,
                        label=f"Chạm BB Lower ({touch_lower.sum()} phiên)")

        ax1.set_title(f"{ticker} — Bollinger Bands (20 ngày, ±2σ) "
                      f"| {lookback_years} năm gần nhất",
                      fontsize=14, fontweight="bold", pad=12)
        ax1.set_ylabel("Giá (nghìn VNĐ)", fontsize=11)
        ax1.legend(loc="upper left", fontsize=8, framealpha=0.8)
        ax1.grid(axis="y", linestyle=":", alpha=0.4)
        ax1.tick_params(labelbottom=False)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))

        # ── Panel dưới: %B (vị trí giá trong dải BB) ────────
        # %B = (Close - BB_Lower) / (BB_Upper - BB_Lower)
        # %B > 1 → phá trên, %B < 0 → phá dưới, %B = 0.5 → giữa
        ax2.set_facecolor("#ffffff")
        band_width = df["bb_upper"] - df["bb_lower"]
        pct_b = (df["close"] - df["bb_lower"]) / band_width.replace(0, float("nan"))

        ax2.plot(df.index, pct_b, color="#9467bd", linewidth=1.2)
        ax2.axhline(1.0, color="#d62728", linestyle="--", linewidth=0.8, alpha=0.7)
        ax2.axhline(0.5, color="#ff7f0e", linestyle=":", linewidth=0.8, alpha=0.7)
        ax2.axhline(0.0, color="#2ca02c", linestyle="--", linewidth=0.8, alpha=0.7)
        ax2.fill_between(df.index, pct_b, 0.5,
                         where=(pct_b > 0.5), alpha=0.15, color="#d62728")
        ax2.fill_between(df.index, pct_b, 0.5,
                         where=(pct_b < 0.5), alpha=0.15, color="#2ca02c")

        ax2.set_ylabel("%B", fontsize=10)
        ax2.set_xlabel("Ngày", fontsize=11)
        ax2.set_ylim(-0.3, 1.3)
        ax2.grid(axis="y", linestyle=":", alpha=0.4)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha="right")

        plt.tight_layout()
        out = output_dir / f"bollinger_{ticker}.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"Đã lưu Bollinger chart → {out.name}")
