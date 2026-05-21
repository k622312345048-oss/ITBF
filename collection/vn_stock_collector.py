"""Thu thập dữ liệu lịch sử toàn bộ cổ phiếu niêm yết Việt Nam.

Nguồn: VCI (VietCap) qua thư viện vnstock.
Bao gồm HOSE, HNX, UPCOM (~1535 mã).
Mỗi mã lấy từ ngày đầu niêm yết đến hiện tại.
"""

import logging
import time
import warnings
from datetime import date
from pathlib import Path

import pandas as pd

from config import settings
from collection.base_collector import BaseCollector

# Tắt deprecation warnings của vnstock
warnings.filterwarnings("ignore", category=DeprecationWarning)
logger = logging.getLogger(__name__)

START_DATE = "2000-01-01"   # Trước khi HOSE mở cửa (2000-07-28) để đảm bảo không bỏ sót


class VNStockCollector(BaseCollector):
    """Thu thập OHLCV toàn bộ cổ phiếu VN từ ngày IPO đến hôm nay.

    - Tự động lấy danh sách 1535+ mã từ vnstock
    - Bỏ qua file đã tải (resume sau khi gián đoạn)
    - Delay giữa mỗi mã để tránh rate-limit
    """

    SLEEP_BETWEEN = 1.0      # giây giữa mỗi mã
    BATCH_SIZE    = 50       # sau mỗi batch in tiến độ
    SLEEP_BATCH   = 3.0      # giây nghỉ giữa các batch

    def get_all_symbols(self) -> pd.DataFrame:
        """Lấy danh sách toàn bộ mã niêm yết kèm sàn giao dịch."""
        from vnstock.api.listing import Listing
        logger.info("Đang lấy danh sách toàn bộ mã chứng khoán VN...")
        df = Listing().symbols_by_exchange()
        # Chỉ lấy cổ phiếu (loại bỏ chứng chỉ quỹ, trái phiếu)
        if "type" in df.columns:
            df = df[df["type"] == "stock"].copy()
        logger.info(f"Tổng cộng {len(df)} mã cổ phiếu: "
                    f"{df['exchange'].value_counts().to_dict()}")
        return df

    def collect(self, symbols: list[str] | None = None, force_reload: bool = False) -> None:
        """Tải dữ liệu lịch sử cho danh sách mã (mặc định = toàn sàn).

        Args:
            symbols:      Danh sách mã cụ thể, hoặc None để lấy toàn sàn.
            force_reload: True = tải lại dù file đã tồn tại.
        """
        settings.ensure_dirs()

        if symbols is None:
            symbol_df = self.get_all_symbols()
            symbols = symbol_df["symbol"].tolist()

        today = date.today().strftime("%Y-%m-%d")
        total = len(symbols)
        success, skipped, failed = 0, 0, []

        logger.info(f"Bắt đầu tải {total} mã từ {START_DATE} đến {today}")

        for i, symbol in enumerate(symbols, start=1):
            out = settings.raw_data_dir / f"stock_{symbol}.csv"

            # Bỏ qua nếu đã có file (trừ khi force_reload=True)
            if out.exists() and not force_reload:
                skipped += 1
                if i % 100 == 0:
                    logger.info(f"[{i}/{total}] Bỏ qua (đã có): {symbol}")
                continue

            df = self._fetch_with_retry(self._download_one, symbol, today)

            if df is None or df.empty:
                failed.append(symbol)
                logger.warning(f"[{i}/{total}] KHÔNG có dữ liệu: {symbol}")
            else:
                df.to_csv(out, index=False)
                success += 1
                if i % 10 == 0 or i <= 5:
                    logger.info(f"[{i}/{total}] {symbol}: {len(df)} phiên "
                                f"({df['time'].iloc[0].date()} → {df['time'].iloc[-1].date()})")

            # Nghỉ giữa mỗi mã
            time.sleep(self.SLEEP_BETWEEN)

            # Nghỉ dài hơn sau mỗi batch
            if i % self.BATCH_SIZE == 0:
                logger.info(f"--- Batch {i//self.BATCH_SIZE}: {success} OK, "
                            f"{skipped} bỏ qua, {len(failed)} lỗi ---")
                time.sleep(self.SLEEP_BATCH)

        logger.info(f"\n=== HOÀN THÀNH ===")
        logger.info(f"  Tải thành công : {success}")
        logger.info(f"  Bỏ qua (có sẵn): {skipped}")
        logger.info(f"  Thất bại       : {len(failed)}")
        if failed:
            logger.warning(f"  Các mã lỗi: {failed}")

    def _download_one(self, symbol: str, end_date: str) -> pd.DataFrame | None:
        """Tải OHLCV từ ngày đầu đến end_date cho 1 mã."""
        try:
            from vnstock.api.quote import Quote
            df = Quote(symbol=symbol, source="VCI").history(
                start=START_DATE,
                end=end_date,
                interval="1D",
            )
            if df is None or df.empty:
                return None

            # Chuẩn hoá kiểu dữ liệu
            df["time"] = pd.to_datetime(df["time"])
            for col in ["open", "high", "low", "close"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)

            return df.sort_values("time").reset_index(drop=True)

        except Exception as e:
            logger.debug(f"Lỗi tải {symbol}: {e}")
            return None
