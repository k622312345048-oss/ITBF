# FinAgent — AI-Powered Financial Data Agent

> Midterm project — IT Application in Banking and Finance (2026)

An end-to-end pipeline that collects financial data, cleans it, visualizes it, and generates AI-powered analysis using Claude.

## Project Structure

```
finagent/
├── collection/        # Data collection (yfinance, Alpha Vantage, NewsAPI)
├── processing/        # Cleaning, feature engineering, validation
├── visualization/     # 4 chart types (trend, heatmap, distribution, Bollinger)
├── analysis/          # Claude AI analysis & report generation
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
```

## Data Sources

| Source | Data Type | Library |
|---|---|---|
| Yahoo Finance | Stock prices (OHLCV), commodities | `yfinance` |
| Alpha Vantage | FX rates, additional indicators | `alpha-vantage` |
| NewsAPI | Financial news headlines | `newsapi-python` |

## Tracked Assets

- **Stocks (VN):** VNM.VN, HPG.VN, FPT.VN
- **Stocks (US):** AAPL, MSFT
- **Macro:** Gold (`GC=F`), Crude Oil (`CL=F`)

## Features

- Robust data collection with retry/rate-limit handling
- Cleaning pipeline: missing values, duplicates, outlier flagging
- Feature engineering: daily returns, MA 7/30d, volatility, Bollinger Bands
- 4 chart types: trend+volume, correlation heatmap, returns distribution, Bollinger
- Claude-powered analysis: trend summary, anomaly detection, risk commentary, asset comparison

## Running Tests

```bash
pytest tests/ -v
```

## API Keys Required

| Key | Where to get |
|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com |
| `ALPHA_VANTAGE_API_KEY` | https://www.alphavantage.co/support/#api-key |
| `NEWS_API_KEY` | https://newsapi.org/register |

**Never commit your `.env` file.**

## Team

| Member | Module |
|---|---|
| Member A | `collection/` + `config.py` |
| Member B | `processing/` + `tests/` |
| Member C | `visualization/` |
| Member D | `analysis/` + `main.py` + `README.md` |
