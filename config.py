from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).parent


class Settings(BaseSettings):
    # API Keys
    anthropic_api_key: str = ""
    news_api_key: str = ""

    # Pipeline defaults
    default_period: str = "6mo"

    # Cổ phiếu Việt Nam (HOSE, đuôi .VN)
    # Bắt đầu với VNM + HPG, thêm mã khác vào đây khi cần
    stock_tickers: list[str] = [
        "VNM.VN",   # Vinamilk
        "HPG.VN",   # Hòa Phát Group
    ]

    # Chỉ số vĩ mô
    macro_symbols: list[str] = [
        "GC=F",      # Giá vàng thế giới (USD/oz)
        "USDVND=X",  # Tỷ giá USD/VNĐ (1 USD = ~25,000 VNĐ)
    ]

    # Paths
    raw_data_dir: Path = BASE_DIR / "data" / "raw"
    processed_data_dir: Path = BASE_DIR / "data" / "processed"
    charts_dir: Path = BASE_DIR / "reports" / "charts"
    analysis_dir: Path = BASE_DIR / "reports" / "analysis"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def ensure_dirs(self):
        for d in [self.raw_data_dir, self.processed_data_dir,
                  self.charts_dir, self.analysis_dir]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
