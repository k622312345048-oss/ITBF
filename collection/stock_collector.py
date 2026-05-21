import logging
import time

import pandas as pd
import yfinance as yf

from config import settings
from collection.base_collector import BaseCollector

logger = logging.getLogger(__name__)

# Tên hiển thị đẹp cho từng mã — dùng trong log và report
TICKER_NAMES = {
    "VNM.VN": "Vinamilk",
    "HPG.VN": "Hòa Phát Group",
    "FPT.VN": "FPT Corporation",
    "VIC.VN": "Vingroup",
    "VHM.VN": "Vinhomes",
}


class StockCollector(BaseCollector):
    """Thu thập dữ liệu giá cổ phiếu OHLCV qua yfinance.

    Hỗ trợ cổ phiếu Việt Nam (đuôi .VN, ví dụ VNM.VN)
    và cổ phiếu quốc tế (AAPL, MSFT, ...).
    Dữ liệu giá VN trả về đơn vị VNĐ.
    """

    # Dừng giữa mỗi ticker để không bị rate-limit
    SLEEP_BETWEEN = 1.5  # giây

    def collect(self, tickers: list[str], period: str = "6mo") -> None:
        settings.ensure_dirs()
        for i, ticker in enumerate(tickers):
            name = TICKER_NAMES.get(ticker, ticker)
            logger.info(f"[{i+1}/{len(tickers)}] Đang tải: {ticker} ({name})")

            df = self._fetch_with_retry(self._download, ticker, period)

            if df.empty:
                logger.warning(f"Không có dữ liệu cho {ticker} — bỏ qua.")
                continue

            # Lưu file: VNM.VN → stock_VNM_VN.csv
            safe = ticker.replace(".", "_").replace("=", "_")
            out = settings.raw_data_dir / f"stock_{safe}.csv"
            df.to_csv(out)
            logger.info(f"Đã lưu {len(df)} phiên → {out.name}")

            # Tránh rate-limit (trừ ticker cuối)
            if i < len(tickers) - 1:
                time.sleep(self.SLEEP_BETWEEN)

    def _download(self, ticker: str, period: str) -> pd.DataFrame:
        raw = yf.download(ticker, period=period, auto_adjust=True, progress=False)

        if raw.empty:
            return raw

        # yfinance trả về MultiIndex columns: (Price, Ticker)
        # Ví dụ: ('Close', 'VNM.VN'), ('Open', 'VNM.VN'), ...
        # Cần flatten xuống 1 level và đổi sang chữ thường
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0).str.lower()
        else:
            raw.columns = raw.columns.str.lower()

        raw.index.name = "date"
        raw.index = pd.to_datetime(raw.index)

        # Xóa những ngày không có giao dịch (volume = 0 hoặc NaN toàn bộ)
        raw = raw.dropna(how="all")

        return raw
