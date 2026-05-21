import logging
import time

import pandas as pd
import yfinance as yf

from config import settings
from collection.base_collector import BaseCollector

logger = logging.getLogger(__name__)

# Tên hiển thị cho từng symbol
SYMBOL_NAMES = {
    "GC=F":      "Giá Vàng (USD/oz)",
    "CL=F":      "Giá Dầu WTI (USD/barrel)",
    "USDVND=X":  "Tỷ giá USD/VNĐ (~25,000 VNĐ/USD)",
    "SI=F":      "Giá Bạc (USD/oz)",
}


class MacroCollector(BaseCollector):
    """Thu thập chỉ số kinh tế vĩ mô qua yfinance.

    Nguồn dữ liệu thứ 2 của pipeline (bên cạnh cổ phiếu).
    Bao gồm: giá vàng, giá dầu, tỷ giá VNĐ/USD.
    """

    SLEEP_BETWEEN = 1.5  # giây

    def collect(self, symbols: list[str], period: str = "6mo") -> None:
        settings.ensure_dirs()
        for i, symbol in enumerate(symbols):
            name = SYMBOL_NAMES.get(symbol, symbol)
            logger.info(f"[{i+1}/{len(symbols)}] Đang tải macro: {symbol} ({name})")

            df = self._fetch_with_retry(self._download, symbol, period)

            if df.empty:
                logger.warning(f"Không có dữ liệu cho {symbol} — bỏ qua.")
                continue

            # Lưu file: GC=F → macro_GC_F.csv
            safe = symbol.replace("=", "_").replace("/", "_").replace("^", "")
            out = settings.raw_data_dir / f"macro_{safe}.csv"
            df.to_csv(out)
            logger.info(f"Đã lưu {len(df)} phiên → {out.name}")

            if i < len(symbols) - 1:
                time.sleep(self.SLEEP_BETWEEN)

    def _download(self, symbol: str, period: str) -> pd.DataFrame:
        raw = yf.download(symbol, period=period, auto_adjust=True, progress=False)

        if raw.empty:
            return raw

        # Flatten MultiIndex columns
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0).str.lower()
        else:
            raw.columns = raw.columns.str.lower()

        raw.index.name = "date"
        raw.index = pd.to_datetime(raw.index)
        raw = raw.dropna(how="all")

        return raw
