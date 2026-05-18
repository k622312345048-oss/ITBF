import logging
import time
from abc import ABC, abstractmethod

import pandas as pd

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds

    def _fetch_with_retry(self, fetch_fn, *args, **kwargs) -> pd.DataFrame:
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                return fetch_fn(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{self.MAX_RETRIES} failed: {e}")
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY * attempt)
        raise RuntimeError(f"All {self.MAX_RETRIES} attempts failed.")

    @abstractmethod
    def collect(self, *args, **kwargs):
        pass
