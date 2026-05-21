"""Thu thập dữ liệu kinh tế vĩ mô và chỉ số thị trường toàn cầu.

Nguồn: Yahoo Finance qua yfinance.
Bao gồm: hàng hoá, ngoại tệ, chỉ số chứng khoán, năng lượng.
"""

import logging
import time

import pandas as pd
import yfinance as yf

from config import settings
from collection.base_collector import BaseCollector

logger = logging.getLogger(__name__)

# Toàn bộ chỉ số macro cần thu thập
MACRO_SYMBOLS = {
    # ── Hàng hoá ──────────────────────────────────────────────
    "GC=F":       "Giá vàng (USD/oz)",
    "SI=F":       "Giá bạc (USD/oz)",
    "HG=F":       "Giá đồng (USD/lb)",
    "CL=F":       "Giá dầu WTI (USD/barrel)",
    "BZ=F":       "Giá dầu Brent (USD/barrel)",
    "NG=F":       "Giá khí tự nhiên (USD/MMBtu)",

    # ── Ngoại tệ ──────────────────────────────────────────────
    "USDVND=X":   "Tỷ giá USD/VNĐ",
    "EURUSD=X":   "Tỷ giá EUR/USD",
    "USDJPY=X":   "Tỷ giá USD/JPY",
    "USDCNY=X":   "Tỷ giá USD/CNY",
    "DX-Y.NYB":   "Chỉ số Dollar Index (DXY)",

    # ── Chỉ số chứng khoán quốc tế ────────────────────────────
    "^GSPC":      "S&P 500 (Mỹ)",
    "^DJI":       "Dow Jones (Mỹ)",
    "^IXIC":      "Nasdaq Composite (Mỹ)",
    "^N225":      "Nikkei 225 (Nhật)",
    "000001.SS":  "Shanghai Composite (Trung Quốc)",
    "^HSI":       "Hang Seng (Hồng Kông)",

    # ── Chỉ số VN (qua yfinance) ──────────────────────────────
    "^VNINDEX":   "VN-Index",

    # ── Biến động thị trường ───────────────────────────────────
    "^VIX":       "VIX (Chỉ số sợ hãi)",

    # ── Tiền điện tử (tham chiếu) ─────────────────────────────
    "BTC-USD":    "Bitcoin (USD)",
}


class MacroCollector(BaseCollector):
    """Thu thập toàn bộ chỉ số kinh tế vĩ mô qua yfinance.

    Là nguồn dữ liệu thứ 2 của pipeline bên cạnh cổ phiếu VN.
    Lấy toàn bộ lịch sử có sẵn (period='max').
    """

    SLEEP_BETWEEN = 1.5   # giây giữa mỗi symbol

    def collect(self, symbols: list[str] | None = None,
                force_reload: bool = False) -> None:
        """Tải macro data.

        Args:
            symbols:      Danh sách symbol, mặc định là MACRO_SYMBOLS.
            force_reload: True = tải lại dù file đã tồn tại.
        """
        settings.ensure_dirs()
        target = symbols if symbols is not None else list(MACRO_SYMBOLS.keys())
        total = len(target)

        logger.info(f"Bắt đầu tải {total} chỉ số macro (full history)")

        for i, symbol in enumerate(target, start=1):
            name = MACRO_SYMBOLS.get(symbol, symbol)
            safe = symbol.replace("=", "_").replace("/", "_").replace("^", "").replace("-", "_")
            out = settings.raw_data_dir / f"macro_{safe}.csv"

            if out.exists() and not force_reload:
                logger.info(f"[{i}/{total}] Bỏ qua (đã có): {symbol} ({name})")
                continue

            logger.info(f"[{i}/{total}] Đang tải: {symbol} — {name}")
            df = self._fetch_with_retry(self._download, symbol)

            if df is None or df.empty:
                logger.warning(f"  Không có dữ liệu cho {symbol}")
                continue

            df.to_csv(out)
            logger.info(f"  Đã lưu {len(df)} phiên "
                        f"({df.index[0].date()} → {df.index[-1].date()}) → {out.name}")

            if i < total:
                time.sleep(self.SLEEP_BETWEEN)

    def _download(self, symbol: str) -> pd.DataFrame | None:
        """Tải toàn bộ lịch sử (period='max') cho 1 symbol."""
        try:
            raw = yf.download(symbol, period="max", auto_adjust=True, progress=False)
            if raw is None or raw.empty:
                return None

            # Flatten MultiIndex columns (yfinance trả về 2 tầng header)
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.get_level_values(0).str.lower()
            else:
                raw.columns = raw.columns.str.lower()

            raw.index.name = "date"
            raw.index = pd.to_datetime(raw.index)
            return raw.dropna(how="all")

        except Exception as e:
            logger.debug(f"Lỗi tải {symbol}: {e}")
            return None
