# FinAgent — AI-Powered Financial Data Agent

> Midterm project — IT Application in Banking and Finance (2026)

An end-to-end pipeline that collects financial data, cleans it, visualizes it, and generates AI-powered analysis using Claude.

## Project Structure

```
finagent/
├── collection/        # Data collection (vnstock, yfinance)
├── processing/        # Cleaning, feature engineering, validation
├── visualization/     # 4 chart types (trend, heatmap, distribution, Bollinger)
├── analysis/          # Claude AI analysis & interactive agent
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
|---|---|---|
| VCI (vnstock) | VN stock prices OHLCV (full history) | `vnstock` |
| Yahoo Finance | Macro indicators (gold, oil, FX, S&P 500) | `yfinance` |

## Tracked Assets

**Vietnamese Stocks (10 mã):**
VNM (Vinamilk), HPG (Hòa Phát), FPT (FPT Corp), MWG (Thế Giới Di Động),
VCB (Vietcombank), TCB (Techcombank), VHM (Vinhomes), GAS (PV GAS),
VIC (Vingroup), VIX (Chứng khoán VIX)

**Market Benchmark:** VNINDEX (VN-Index)

**Macro Indicators (4):**
USDVND (Tỷ giá USD/VNĐ), GC=F (Vàng), CL=F (Dầu WTI), ^GSPC (S&P 500)

## Features

- Robust data collection with retry/rate-limit handling
- Cleaning pipeline: missing values, duplicates, outlier flagging
- Feature engineering: daily returns, MA 7/30d, volatility, Bollinger Bands
- 4 chart types: trend+volume, correlation heatmap, returns distribution, Bollinger Bands
- Claude-powered analysis: trend summary, anomaly detection, risk commentary, asset comparison
- Interactive AI chatbot (`agent.py`) with tool use

## Running Tests

```bash
pytest tests/ -v
```

## API Keys Required

| Key | Where to get |
|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com |
| `NEWS_API_KEY` | https://newsapi.org/register |

**Never commit your `.env` file.**

## Team — Nhóm 9

| Thành viên | Module |
|---|---|
| Nguyễn Trần Hoàng Phúc | `collection/` + `config.py` |
| Trương Ngọc Nga | `processing/` + `tests/` |
| Hà Phương Ngân | `visualization/` + `analysis/` + `main.py` |
