"""Thu thập dữ liệu lịch sử toàn bộ cổ phiếu niêm yết Việt Nam.

Nguồn: VCI (VietCap) qua thư viện vnstock.
Bao gồm HOSE, HNX, UPCOM (~1535 mã).
Mỗi mã lấy từ ngày đầu niêm yết đến hiện tại.

Rate limit của vnstock (guest): 20 req/phút.
→ Dùng 3.5s sleep giữa mỗi mã để ở dưới ngưỡng an toàn.
→ Ước tính: 1535 mã × 3.5s ≈ 90 phút.
→ Resume được: chạy lại tự bỏ qua file đã có.
"""

import logging
import time
import warnings
from datetime import date

import pandas as pd

from config import settings
from collection.base_collector import BaseCollector

warnings.filterwarnings("ignore", category=DeprecationWarning)
logger = logging.getLogger(__name__)

START_DATE       = "2000-01-01"  # Trước ngày HOSE mở cửa 28/07/2000
RATE_LIMIT_PAUSE = 60.0          # Giây chờ khi bị rate-limit
SLEEP_BETWEEN    = 3.5           # Giây giữa mỗi mã (≤17 req/phút, an toàn với guest)
SLEEP_BATCH      = 5.0           # Giây nghỉ thêm sau mỗi 50 mã
BATCH_SIZE       = 50


class VNStockCollector(BaseCollector):
    """Thu thập OHLCV toàn bộ cổ phiếu VN từ ngày IPO đến hôm nay."""

    MAX_RETRIES = 4   # ghi đè BaseCollector

    def get_all_symbols(self) -> pd.DataFrame:
        """Lấy danh sách toàn bộ mã niêm yết kèm sàn giao dịch."""
        from vnstock.api.listing import Listing
        logger.info("Đang lấy danh sách toàn bộ mã chứng khoán VN...")
        df = Listing().symbols_by_exchange()
        if "type" in df.columns:
            df = df[df["type"] == "stock"].copy()
        exchange_counts = df["exchange"].value_counts().to_dict() if "exchange" in df.columns else {}
        logger.info(f"Tổng {len(df)} mã: {exchange_counts}")
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

        logger.info(f"Bắt đầu tải {total} mã | {START_DATE} → {today}")
        logger.info(f"Sleep {SLEEP_BETWEEN}s/mã → ước tính {total * SLEEP_BETWEEN / 60:.0f} phút")

        for i, symbol in enumerate(symbols, start=1):
            out = settings.raw_data_dir / f"stock_{symbol}.csv"

            if out.exists() and not force_reload:
                skipped += 1
                if i % 200 == 0:
                    logger.info(f"[{i}/{total}] {skipped} bỏ qua, {success} mới, {len(failed)} lỗi")
                continue

            df = self._download_with_ratelimit(symbol, today)

            if df is None or df.empty:
                failed.append(symbol)
                logger.warning(f"[{i}/{total}] Không có dữ liệu: {symbol}")
            else:
                df.to_csv(out, index=False)
                success += 1
                if i % 20 == 0 or i <= 3:
                    first = df["time"].iloc[0].date()
                    last  = df["time"].iloc[-1].date()
                    logger.info(f"[{i}/{total}] {symbol}: {len(df)} phiên ({first} → {last})")

            time.sleep(SLEEP_BETWEEN)

            if i % BATCH_SIZE == 0:
                pct = i / total * 100
                logger.info(f"[{i}/{total} | {pct:.0f}%] batch done — "
                            f"{success} OK, {skipped} skip, {len(failed)} fail")
                time.sleep(SLEEP_BATCH)

        logger.info("=== HOÀN THÀNH THU THẬP CỔ PHIẾU ===")
        logger.info(f"  Thành công : {success}")
        logger.info(f"  Bỏ qua    : {skipped}")
        logger.info(f"  Thất bại  : {len(failed)}")
        if failed:
            # Lưu danh sách mã lỗi để tải lại sau
            fail_path = settings.raw_data_dir / "_failed_symbols.txt"
            fail_path.write_text("\n".join(failed))
            logger.warning(f"  Mã lỗi đã lưu → {fail_path.name}")

    def _download_with_ratelimit(self, symbol: str, end_date: str) -> pd.DataFrame | None:
        """Tải 1 mã, tự chờ và thử lại khi bị rate-limit."""
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                return self._download_one(symbol, end_date)
            except Exception as e:
                err = str(e).lower()
                if "rate limit" in err or "giới hạn" in err or "limit" in err:
                    wait = RATE_LIMIT_PAUSE * attempt
                    logger.warning(f"  Rate-limit trên {symbol} (lần {attempt}). Chờ {wait:.0f}s...")
                    time.sleep(wait)
                else:
                    logger.debug(f"  Lỗi {symbol} lần {attempt}: {e}")
                    if attempt < self.MAX_RETRIES:
                        time.sleep(2 * attempt)
        return None

    def _download_one(self, symbol: str, end_date: str) -> pd.DataFrame | None:
        from vnstock.api.quote import Quote
        df = Quote(symbol=symbol, source="VCI").history(
            start=START_DATE,
            end=end_date,
            interval="1D",
        )
        if df is None or df.empty:
            return None

        df["time"] = pd.to_datetime(df["time"])
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)

        return df.sort_values("time").reset_index(drop=True)
