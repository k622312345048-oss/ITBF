from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).parent


class Settings(BaseSettings):
    # API Keys
    groq_api_key: str = ""
    news_api_key: str = ""

    # Chỉ số vĩ mô
    macro_symbols: list[str] = [
        "USDVND=X",  # Tỷ giá USD/VNĐ
        "GC=F",      # Giá vàng thế giới (USD/oz)
        "CL=F",      # Giá dầu WTI (USD/barrel)
        "^GSPC",     # S&P 500 (dòng vốn ngoại)
    ]

    # Paths
    raw_data_dir: Path       = BASE_DIR / "data" / "raw"
    processed_data_dir: Path = BASE_DIR / "data" / "processed"
    charts_dir: Path         = BASE_DIR / "reports" / "charts"
    analysis_dir: Path       = BASE_DIR / "reports" / "analysis"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def ensure_dirs(self):
        for d in [self.raw_data_dir, self.processed_data_dir,
                  self.charts_dir, self.analysis_dir]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
