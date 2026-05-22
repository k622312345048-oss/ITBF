# FinAgent — AI-Powered Financial Data Agent

> Midterm project — IT Application in Banking and Finance (2026)

An end-to-end pipeline that collects financial data from multiple sources, cleans and processes it, generates publication-quality visualizations, and delivers AI-powered analysis using LLaMA 3.3 70B (via Groq).

## Project Structure

```
ITBF/
├── README.md
├── requirements.txt
├── config.py                        # Settings & paths (Pydantic)
├── main.py                          # CLI pipeline runner
├── agent.py                         # Interactive AI chatbot entry point
├── .env.example                     # API key template
│
├── collection/
│   ├── base_collector.py            # Retry/rate-limit base class
│   ├── vn_stock_collector.py        # vnstock OHLCV (full market, parallel)
│   ├── macro_collector.py           # yfinance macro indicators
│   └── news_collector.py            # NewsAPI headlines
│
├── processing/
│   ├── cleaner.py                   # Missing values, dedup, outlier flagging
│   ├── feature_engineer.py          # Returns, MA 7/30d, volatility, Bollinger
│   ├── validator.py                 # Schema & range checks
│   └── news_processor.py           # Sentiment scoring from headlines
│
├── visualization/
│   ├── trend_chart.py               # Price trend + volume overlay
│   ├── heatmap.py                   # Correlation heatmap
│   ├── distribution.py              # Daily returns histogram/KDE
│   └── rolling_stats.py            # Moving averages & Bollinger Bands
│
├── analysis/
│   ├── agent.py                     # FinAgent — Groq tool-use loop
│   ├── tools.py                     # Tool schemas & implementations
│   ├── analyzer.py                  # Batch AI report generator
│   ├── prompt_builder.py            # Structured LLM prompt builders
│   └── llm_client.py               # Groq API wrapper
│
├── data/                            # git-ignored
│   ├── raw/                         # Downloaded CSVs
│   └── processed/                   # Cleaned + feature-engineered CSVs
│
├── reports/                         # git-ignored
│   ├── charts/                      # Generated PNG charts
│   └── analysis/                    # AI-generated Markdown reports
│
└── tests/
    ├── test_collection.py
    └── test_processing.py
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
# Run full pipeline (full market + macro + news)
python main.py --all

# Run individual steps
python main.py --step collect-market        # Full HOSE + HNX + UPCoM (~1500 stocks)
python main.py --step process               # Process all files in raw/
python main.py --step process-watch         # Daemon: auto-process as new files arrive
python main.py --step visualize             # Default 11 representative stocks
python main.py --step visualize --tickers VNM,HPG,FPT   # Custom tickers
python main.py --step analyze               # AI analysis for all processed stocks
python main.py --step analyze --top 20      # Top 20 most liquid stocks only

# Interactive AI chatbot — supports ANY Vietnamese stock on demand
python agent.py
```

## Data Sources

| Source | Data Type | Library |
|--------|-----------|---------|
| VCI (vnstock) | VN stock prices OHLCV (full history) | `vnstock` |
| Yahoo Finance | Macro indicators (gold, oil, FX, S&P 500) | `yfinance` |
| NewsAPI | Financial news headlines & sentiment | `newsapi-python` |

## Tracked Assets

**Vietnamese Stocks:** Full market — all stocks on HOSE, HNX, and UPCoM (~1,500 tickers via `--step collect-market`).

The AI agent (`agent.py`) can fetch and analyse **any Vietnamese stock on demand** — just ask about a ticker not yet in cache and it will download automatically.

**Macro Indicators (4):**
USDVND (Tỷ giá USD/VNĐ), GC=F (Vàng), CL=F (Dầu WTI), ^GSPC (S&P 500)

## Features

- Full Vietnamese market collection (~1,500 stocks, parallel download with rate-limit handling)
- On-demand fetch: agent auto-downloads any VN stock not yet in cache
- Cleaning pipeline: missing values (forward-fill), duplicate removal, outlier flagging
- Feature engineering: daily returns, MA 7/30d, annualised volatility, Bollinger Bands
- News sentiment scoring with Vietnam market-level context
- 4 chart types: trend+volume, correlation heatmap, returns distribution, Bollinger Bands
- AI-powered analysis (LLaMA 3.3 70B via Groq): trend summary, anomaly detection, risk commentary, asset comparison
- Interactive AI chatbot (`agent.py`) with tool use — supports any ticker on HOSE/HNX/UPCoM

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
