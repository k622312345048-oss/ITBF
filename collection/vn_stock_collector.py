"""Thu thập dữ liệu lịch sử cổ phiếu Việt Nam qua vnstock (nguồn VCI).

Rate limit (guest): 20 req/phút → sleep 4.5s/mã.
Resume được: chạy lại tự bỏ qua file đã có.
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
RATE_LIMIT_PAUSE = 90.0          # Giây chờ khi bị rate-limit
SLEEP_BETWEEN    = 4.5           # Giây giữa mỗi mã (≤13 req/phút, an toàn với guest)
SLEEP_BATCH      = 5.0           # Giây nghỉ thêm sau mỗi 50 mã
BATCH_SIZE       = 50


class VNStockCollector(BaseCollector):
    """Thu thập OHLCV cổ phiếu VN từ ngày IPO đến hôm nay."""

    MAX_RETRIES = 4   # ghi đè BaseCollector

    def collect(self, symbols: list[str], force_reload: bool = False) -> None:
        settings.ensure_dirs()
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
        """Tải 1 mã, tự chờ và thử lại khi bị rate-limit.

        vnstock gọi sys.exit() khi rate-limit → bắt SystemExit (BaseException),
        không phải Exception thông thường.
        """
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                return self._download_one(symbol, end_date)
            except SystemExit:
                # vnstock gọi sys.exit() khi bị rate-limit
                wait = RATE_LIMIT_PAUSE * attempt
                logger.warning(f"  Rate-limit (sys.exit) trên {symbol} lần {attempt}. Chờ {wait:.0f}s...")
                time.sleep(wait)
            except Exception as e:
                err = str(e).lower()
                if "rate limit" in err or "giới hạn" in err or "limit" in err:
                    wait = RATE_LIMIT_PAUSE * attempt
                    logger.warning(f"  Rate-limit trên {symbol} lần {attempt}. Chờ {wait:.0f}s...")
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
