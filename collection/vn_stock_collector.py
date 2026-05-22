"""Thu thập dữ liệu lịch sử cổ phiếu Việt Nam qua vnstock (nguồn VCI).

Rate limit (guest): ~20 req/phút.
Parallel: 3 workers, mỗi worker sleep 3s → ~3 req/3s burst, retry khi bị limit.
Resume được: chạy lại tự bỏ qua file đã có.
"""

import logging
import time
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pandas as pd

from config import settings
from collection.base_collector import BaseCollector

warnings.filterwarnings("ignore", category=DeprecationWarning)
logger = logging.getLogger(__name__)

ACTIVE_EXCHANGES = {"HSX", "HNX", "UPCOM"}
START_DATE       = "2000-01-01"
RATE_LIMIT_PAUSE = 30.0   # Giảm từ 90s → 30s: recover nhanh hơn khi bị limit
SLEEP_BETWEEN    = 3.0    # Giảm từ 4.5s → 3.0s (20 req/phút)
WORKERS          = 3      # Parallel workers
BATCH_SIZE       = 50


def get_all_market_tickers() -> list[str]:
    """Trả về danh sách tất cả cổ phiếu (type=STOCK) trên HOSE, HNX, UPCoM."""
    from vnstock.api.listing import Listing
    df = Listing(source="VCI").symbols_by_exchange()
    stocks = df[(df["exchange"].isin(ACTIVE_EXCHANGES)) & (df["type"] == "STOCK")]
    tickers = sorted(stocks["symbol"].str.upper().tolist())
    by_exchange = stocks["exchange"].value_counts()
    logger.info(
        f"Danh sách thị trường: {len(tickers)} cổ phiếu "
        f"(HOSE={by_exchange.get('HSX', 0)}, "
        f"HNX={by_exchange.get('HNX', 0)}, "
        f"UPCoM={by_exchange.get('UPCOM', 0)})"
    )
    return tickers


class VNStockCollector(BaseCollector):
    """Thu thập OHLCV cổ phiếu VN, parallel với global rate limiter.

    Global lock đảm bảo tối thiểu SLEEP_BETWEEN giây giữa bất kỳ 2 API call nào.
    Workers overlap nhau ở phần I/O (ghi file, xử lý data) → nhanh hơn single thread.
    """

    MAX_RETRIES = 4
    _api_lock   = threading.Lock()
    _last_call  = [0.0]

    def collect(self, symbols: list[str], force_reload: bool = False,
                workers: int = WORKERS) -> None:
        settings.ensure_dirs()
        today = date.today().strftime("%Y-%m-%d")
        total = len(symbols)

        to_download = [s for s in symbols
                       if not (settings.raw_data_dir / f"stock_{s}.csv").exists()
                       or force_reload]
        skipped = total - len(to_download)

        logger.info(f"Bắt đầu tải {len(to_download)} mã (bỏ qua {skipped} đã có) "
                    f"| {workers} workers | {START_DATE} → {today}")
        logger.info(f"Ước tính: ~{len(to_download) * SLEEP_BETWEEN / 60:.0f} phút")

        success_count = [0]
        failed: list[str] = []
        done_count = [0]
        _stats_lock = threading.Lock()

        def _worker(symbol: str) -> None:
            # ── Global rate limiter: chờ đến khi slot trống ──
            with self._api_lock:
                elapsed = time.time() - self._last_call[0]
                wait = SLEEP_BETWEEN - elapsed
                if wait > 0:
                    time.sleep(wait)
                self._last_call[0] = time.time()

            df = self._download_with_ratelimit(symbol, today)

            # ── Ghi file và cập nhật stats (I/O overlap giữa các workers) ──
            with _stats_lock:
                done_count[0] += 1
                done = done_count[0]
                n_todo = len(to_download)

                if df is None or df.empty:
                    failed.append(symbol)
                    logger.warning(f"[{done+skipped}/{total}] Không có dữ liệu: {symbol}")
                else:
                    (settings.raw_data_dir / f"stock_{symbol}.csv").write_bytes(
                        df.to_csv(index=False).encode()
                    )
                    success_count[0] += 1
                    if done % 20 == 0 or done <= 3:
                        first = df["time"].iloc[0].date()
                        last  = df["time"].iloc[-1].date()
                        logger.info(f"[{done+skipped}/{total}] {symbol}: "
                                    f"{len(df)} phiên ({first} → {last})")

                if done % BATCH_SIZE == 0 or done == n_todo:
                    pct = (done + skipped) / total * 100
                    logger.info(f"[{done+skipped}/{total} | {pct:.0f}%] "
                                f"{success_count[0]} OK, {skipped} skip, {len(failed)} fail")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            list(executor.map(_worker, to_download))

        logger.info("=== HOÀN THÀNH THU THẬP CỔ PHIẾU ===")
        logger.info(f"  Thành công : {success_count[0]}")
        logger.info(f"  Bỏ qua    : {skipped}")
        logger.info(f"  Thất bại  : {len(failed)}")
        if failed:
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
