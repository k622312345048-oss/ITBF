# FinAgent — AI-Powered Financial Data Agent

> Midterm project — IT Application in Banking and Finance (2026)

An end-to-end pipeline that collects financial data from multiple sources, cleans and processes it, generates publication-quality visualizations, and delivers AI-powered analysis using LLaMA 3.3 70B (via Groq).

## Project Structure

```
finagent/
├── collection/        # Data collection (vnstock, yfinance, NewsAPI)
├── processing/        # Cleaning, feature engineering, validation, news sentiment
├── visualization/     # 4 chart types (trend, heatmap, distribution, Bollinger)
├── analysis/          # AI analysis & interactive agent (Groq / LLaMA 3.3 70B)
├── data/              # raw/ and processed/ CSVs (git-ignored)
├── reports/           # Generated charts and analysis (git-ignored)
└── tests/             # Unit tests
```

## Setup

```bash
# 1. Clone & enter
git clone https://github.com/k622312345048-oss/ITBF.git
cd ITBF

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API keys
cp .env.example .env
# Edit .env and fill in your API keys
```

## Usage

```bash
# Run full pipeline
python main.py --all

# Run individual steps
python main.py --step collect
python main.py --step process
python main.py --step visualize
python main.py --step analyze

# Interactive AI chatbot
python agent.py
```

## Data Sources

| Source | Data Type | Library |
|--------|-----------|---------|
| VCI (vnstock) | VN stock prices OHLCV (full history) | `vnstock` |
| Yahoo Finance | Macro indicators (gold, oil, FX, S&P 500) | `yfinance` |
| NewsAPI | Financial news headlines & sentiment | `newsapi-python` |

## Tracked Assets

**Vietnamese Stocks (10 mã):**
VNM (Vinamilk), HPG (Hòa Phát), FPT (FPT Corp), MWG (Thế Giới Di Động),
VCB (Vietcombank), TCB (Techcombank), VHM (Vinhomes), GAS (PV GAS),
VIC (Vingroup), VIX (Chứng khoán VIX)

**Market Benchmark:** VNINDEX (VN-Index)

**Macro Indicators (4):**
USDVND (Tỷ giá USD/VNĐ), GC=F (Vàng), CL=F (Dầu WTI), ^GSPC (S&P 500)

## Features

- Robust data collection with retry/rate-limit handling (3 sources)
- Cleaning pipeline: missing values (forward-fill), duplicate removal, outlier flagging
- Feature engineering: daily returns, MA 7/30d, annualised volatility, Bollinger Bands
- News sentiment scoring (keyword-based, per ticker per day)
- 4 chart types: trend+volume, correlation heatmap, returns distribution, Bollinger Bands
- AI-powered analysis (LLaMA 3.3 70B via Groq): trend summary, anomaly detection, risk commentary, asset comparison, news sentiment alignment
- Interactive AI chatbot (`agent.py`) with tool use

## Running Tests

```bash
pytest tests/ -v
```

## API Keys Required

| Key | Where to get |
|-----|-------------|
| `GROQ_API_KEY` | https://console.groq.com (free) |
| `NEWS_API_KEY` | https://newsapi.org/register (free) |

**Never commit your `.env` file.**

## Team — Nhóm 9

| Thành viên | Module |
|------------|--------|
| Nguyễn Trần Hoàng Phúc | `collection/` + `config.py` |
| Trương Ngọc Nga | `processing/` + `tests/` |
| Hà Phương Ngân | `visualization/` + `analysis/` + `main.py` |
