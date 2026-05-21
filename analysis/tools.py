"""Định nghĩa và thực thi các tool mà AI agent có thể gọi.

Mỗi tool gồm:
  - schema: mô tả cho Claude biết tool làm gì và nhận tham số gì
  - hàm thực thi: chạy thật và trả kết quả dạng string
"""

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from config import settings

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# TOOL SCHEMAS — Claude đọc để biết khi nào nên gọi tool nào
# ──────────────────────────────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "name": "list_available_stocks",
        "description": (
            "Liệt kê tất cả mã cổ phiếu Việt Nam đang có trong hệ thống. "
            "Dùng khi người dùng hỏi 'có những mã nào', 'mã nào đang có dữ liệu'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_stock_summary",
        "description": (
            "Lấy thống kê tóm tắt của 1 mã cổ phiếu: giá hiện tại, "
            "return theo các kỳ, volatility, MA, Bollinger Bands. "
            "Dùng khi phân tích hoặc hỏi về 1 mã cụ thể."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Mã cổ phiếu, ví dụ: VNM, HPG, FPT",
                },
                "period_days": {
                    "type": "integer",
                    "description": "Số ngày muốn phân tích (30, 90, 180, 365). Mặc định 90.",
                    "default": 90,
                },
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_latest_prices",
        "description": (
            "Lấy giá đóng cửa gần nhất của một hoặc nhiều mã. "
            "Dùng khi hỏi 'giá hiện tại', 'giá hôm nay/hôm qua'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Danh sách mã, ví dụ: ['VNM', 'HPG', 'FPT']",
                },
                "n_days": {
                    "type": "integer",
                    "description": "Số phiên gần nhất cần lấy (mặc định 3).",
                    "default": 3,
                },
            },
            "required": ["tickers"],
        },
    },
    {
        "name": "compare_stocks",
        "description": (
            "So sánh hiệu suất và rủi ro của nhiều mã trong cùng khoảng thời gian. "
            "Trả về bảng return, volatility, Sharpe ratio. "
            "Dùng khi hỏi 'so sánh', 'mã nào tốt hơn', 'đầu tư mã nào'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Danh sách 2-10 mã cần so sánh",
                },
                "period_days": {
                    "type": "integer",
                    "description": "Khoảng thời gian so sánh tính bằng ngày (mặc định 180).",
                    "default": 180,
                },
            },
            "required": ["tickers"],
        },
    },
    {
        "name": "generate_chart",
        "description": (
            "Vẽ biểu đồ và lưu vào reports/charts/. "
            "chart_type: 'trend' (giá + volume), 'bollinger' (Bollinger Bands), "
            "'distribution' (phân phối return), 'heatmap' (tương quan nhiều mã). "
            "Dùng khi người dùng yêu cầu vẽ hoặc hiển thị biểu đồ."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Danh sách mã (1 mã cho trend/bollinger, nhiều mã cho heatmap)",
                },
                "chart_type": {
                    "type": "string",
                    "enum": ["trend", "bollinger", "distribution", "heatmap"],
                    "description": "Loại biểu đồ",
                },
            },
            "required": ["tickers", "chart_type"],
        },
    },
    {
        "name": "get_top_movers",
        "description": (
            "Lấy danh sách mã tăng/giảm mạnh nhất hoặc biến động nhiều nhất "
            "trong N ngày gần nhất. "
            "Dùng khi hỏi 'mã nào tăng/giảm mạnh', 'top movers', 'biến động nhất'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "period_days": {
                    "type": "integer",
                    "description": "Số ngày nhìn lại (mặc định 30).",
                    "default": 30,
                },
                "top_n": {
                    "type": "integer",
                    "description": "Số mã muốn lấy (mặc định 5).",
                    "default": 5,
                },
                "metric": {
                    "type": "string",
                    "enum": ["return", "volatility"],
                    "description": "'return' = lợi nhuận cao nhất, 'volatility' = biến động nhất",
                    "default": "return",
                },
            },
            "required": [],
        },
    },
]


# ──────────────────────────────────────────────────────────────
# TOOL EXECUTOR — chạy tool và trả kết quả dạng string
# ──────────────────────────────────────────────────────────────

def execute_tool(name: str, inputs: dict) -> str:
    """Dispatch tên tool → hàm tương ứng."""
    handlers = {
        "list_available_stocks": _list_available_stocks,
        "get_stock_summary":     _get_stock_summary,
        "get_latest_prices":     _get_latest_prices,
        "compare_stocks":        _compare_stocks,
        "generate_chart":        _generate_chart,
        "get_top_movers":        _get_top_movers,
    }
    if name not in handlers:
        return f"Tool '{name}' không tồn tại."
    try:
        return handlers[name](**inputs)
    except Exception as e:
        logger.error(f"Tool {name} lỗi: {e}")
        return f"Lỗi khi chạy tool {name}: {e}"


# ──────────────────────────────────────────────────────────────
# IMPLEMENTATIONS
# ──────────────────────────────────────────────────────────────

def _load_processed(ticker: str) -> pd.DataFrame | None:
    """Load processed CSV cho 1 mã. Trả None nếu không có."""
    path = settings.processed_data_dir / f"stock_{ticker.upper()}.csv"
    if not path.exists():
        # Thử tải nhanh nếu chưa có trong processed
        raw = settings.raw_data_dir / f"stock_{ticker.upper()}.csv"
        if not raw.exists():
            return None
        from processing.cleaner import Cleaner
        from processing.feature_engineer import FeatureEngineer
        df = Cleaner().clean(raw)
        df = FeatureEngineer().engineer(df)
        return df
    return pd.read_csv(path, index_col=0, parse_dates=True)


def _list_available_stocks() -> str:
    files = sorted(settings.processed_data_dir.glob("stock_*.csv"))
    if not files:
        files = sorted(settings.raw_data_dir.glob("stock_*.csv"))
    tickers = [f.stem.replace("stock_", "").upper() for f in files]
    return (f"Hiện có {len(tickers)} mã cổ phiếu trong hệ thống:\n"
            + ", ".join(tickers))


def _get_stock_summary(ticker: str, period_days: int = 90) -> str:
    df = _load_processed(ticker)
    if df is None:
        return f"Không tìm thấy dữ liệu cho mã {ticker.upper()}."

    recent = df.last(f"{period_days}D")
    if recent.empty:
        return f"Không đủ dữ liệu {period_days} ngày cho {ticker.upper()}."

    close      = recent["close"]
    ret_period = (close.iloc[-1] - close.iloc[0]) / close.iloc[0]
    ret_1w     = (close.iloc[-1] - close.iloc[-6]) / close.iloc[-6] if len(close) >= 6 else float("nan")
    vol        = recent["volatility_30"].iloc[-1] if "volatility_30" in recent.columns else float("nan")
    ma7        = recent["ma_7"].iloc[-1]  if "ma_7"  in recent.columns else float("nan")
    ma30       = recent["ma_30"].iloc[-1] if "ma_30" in recent.columns else float("nan")
    bb_upper   = recent["bb_upper"].iloc[-1] if "bb_upper" in recent.columns else float("nan")
    bb_lower   = recent["bb_lower"].iloc[-1] if "bb_lower" in recent.columns else float("nan")
    outliers   = int(recent["is_outlier"].sum()) if "is_outlier" in recent.columns else 0

    # Tín hiệu MA
    signal = "TĂNG (MA7 > MA30)" if ma7 > ma30 else "GIẢM (MA7 < MA30)"

    return f"""
=== TÓM TẮT: {ticker.upper()} ({period_days} ngày gần nhất) ===
Kỳ phân tích : {recent.index[0].date()} → {recent.index[-1].date()}
Số phiên     : {len(recent)}

GIÁ
  Hiện tại   : {close.iloc[-1]:,.1f} nghìn VNĐ
  Cao nhất   : {close.max():,.1f} nghìn VNĐ
  Thấp nhất  : {close.min():,.1f} nghìn VNĐ
  Return kỳ  : {ret_period*100:+.2f}%
  Return 1W  : {ret_1w*100:+.2f}%

CHỈ BÁO KỸ THUẬT
  MA 7 ngày  : {ma7:,.2f}
  MA 30 ngày : {ma30:,.2f}
  Tín hiệu   : {signal}
  BB Upper   : {bb_upper:,.2f}
  BB Lower   : {bb_lower:,.2f}
  Volatility : {vol*100:.1f}%/năm
  Outliers   : {outliers} phiên bất thường
""".strip()


def _get_latest_prices(tickers: list[str], n_days: int = 3) -> str:
    lines = []
    for ticker in tickers:
        df = _load_processed(ticker)
        if df is None:
            lines.append(f"{ticker.upper()}: không có dữ liệu")
            continue
        last = df["close"].tail(n_days)
        rows = "  ".join(f"{d.date()} → {p:,.1f}K VNĐ"
                         for d, p in zip(last.index, last.values))
        lines.append(f"{ticker.upper()}: {rows}")
    return "\n".join(lines)


def _compare_stocks(tickers: list[str], period_days: int = 180) -> str:
    rows = []
    for ticker in tickers:
        df = _load_processed(ticker)
        if df is None:
            continue
        recent = df.last(f"{period_days}D")
        if len(recent) < 10:
            continue
        ret = (recent["close"].iloc[-1] - recent["close"].iloc[0]) / recent["close"].iloc[0]
        vol = recent["volatility_30"].iloc[-1] if "volatility_30" in recent.columns else float("nan")
        avg_ret = recent["daily_return"].mean() if "daily_return" in recent.columns else float("nan")
        # Sharpe ratio đơn giản (không tính risk-free rate)
        sharpe = (avg_ret / recent["daily_return"].std() * np.sqrt(252)
                  if "daily_return" in recent.columns else float("nan"))
        rows.append({
            "Mã": ticker.upper(),
            "Return": f"{ret*100:+.2f}%",
            "Volatility/năm": f"{vol*100:.1f}%" if not np.isnan(vol) else "N/A",
            "Sharpe": f"{sharpe:.2f}" if not np.isnan(sharpe) else "N/A",
            "Giá hiện tại": f"{recent['close'].iloc[-1]:,.1f}K",
        })

    if not rows:
        return "Không tìm thấy dữ liệu cho các mã được yêu cầu."

    df_result = pd.DataFrame(rows).set_index("Mã")
    header = f"SO SÁNH {len(rows)} MÃ — {period_days} ngày gần nhất\n"
    return header + df_result.to_string()


def _generate_chart(tickers: list[str], chart_type: str) -> str:
    settings.ensure_dirs()
    frames = {}
    for ticker in tickers:
        df = _load_processed(ticker)
        if df is not None:
            frames[f"stock_{ticker.upper()}"] = df

    if not frames:
        return "Không có dữ liệu để vẽ biểu đồ."

    saved = []
    if chart_type == "trend":
        from visualization.trend_chart import plot_trend
        plot_trend(frames, settings.charts_dir)
        saved = [f"trend_{t.upper()}.png" for t in tickers]

    elif chart_type == "bollinger":
        from visualization.rolling_stats import plot_rolling_stats
        plot_rolling_stats(frames, settings.charts_dir)
        saved = [f"bollinger_{t.upper()}.png" for t in tickers]

    elif chart_type == "distribution":
        from visualization.distribution import plot_distribution
        plot_distribution(frames, settings.charts_dir)
        saved = ["returns_distribution.png"]

    elif chart_type == "heatmap":
        from visualization.heatmap import plot_heatmap
        plot_heatmap(frames, settings.charts_dir)
        saved = ["correlation_heatmap.png"]

    paths = [str(settings.charts_dir / f) for f in saved]
    return f"Đã vẽ và lưu {len(paths)} biểu đồ:\n" + "\n".join(paths)


def _get_top_movers(period_days: int = 30, top_n: int = 5,
                    metric: str = "return") -> str:
    results = []
    for f in settings.processed_data_dir.glob("stock_*.csv"):
        ticker = f.stem.replace("stock_", "").upper()
        try:
            df = pd.read_csv(f, index_col=0, parse_dates=True)
            recent = df.last(f"{period_days}D")
            if len(recent) < 5:
                continue
            if metric == "return":
                val = ((recent["close"].iloc[-1] - recent["close"].iloc[0])
                       / recent["close"].iloc[0])
            else:
                val = (recent["volatility_30"].iloc[-1]
                       if "volatility_30" in recent.columns else float("nan"))
            if not np.isnan(val):
                results.append((ticker, val))
        except Exception:
            continue

    if not results:
        return "Không đủ dữ liệu để tính top movers."

    results.sort(key=lambda x: x[1], reverse=True)
    label = "Return" if metric == "return" else "Volatility"
    lines = [f"TOP {top_n} MÃ THEO {label.upper()} — {period_days} ngày gần nhất"]
    lines.append(f"\n{'Tăng mạnh nhất':}")
    for t, v in results[:top_n]:
        lines.append(f"  {t:8s}: {v*100:+.2f}%")
    lines.append(f"\n{'Giảm mạnh nhất':}")
    for t, v in results[-top_n:]:
        lines.append(f"  {t:8s}: {v*100:+.2f}%")
    return "\n".join(lines)
