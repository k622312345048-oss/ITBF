"""Thu thập chỉ số kinh tế vĩ mô qua Yahoo Finance (yfinance)."""

import logging
import time

import pandas as pd
import yfinance as yf

from config import settings
from collection.base_collector import BaseCollector

logger = logging.getLogger(__name__)

MACRO_SYMBOLS = {
    "USDVND=X":  "Tỷ giá USD/VNĐ",
    "GC=F":      "Giá vàng (USD/oz)",
    "CL=F":      "Giá dầu WTI (USD/barrel)",
    "^GSPC":     "S&P 500",
}


class MacroCollector(BaseCollector):
    """Thu thập chỉ số vĩ mô qua yfinance, lấy toàn bộ lịch sử (period='max')."""

    SLEEP_BETWEEN = 1.5   # giây giữa mỗi symbol

    def collect(self, symbols: list[str], force_reload: bool = False) -> None:
        settings.ensure_dirs()
        total = len(symbols)

        logger.info(f"Bắt đầu tải {total} chỉ số macro (full history)")

        for i, symbol in enumerate(symbols, start=1):
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
