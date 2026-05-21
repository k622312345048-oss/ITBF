import pandas as pd


def _fmt(val, fmt: str) -> str:
    try:
        if val is None or pd.isna(val):
            return "N/A"
        return format(val, fmt)
    except Exception:
        return "N/A"


def build_news_context(ticker: str, news_df: pd.DataFrame, days: int = 7) -> str:
    """Tóm tắt Vietnam market news sentiment cho context của LLM.

    Ưu tiên ticker-specific news, fallback về market-level news
    (vì news keywords là 'Vietnam stock market', 'VN-Index' etc. chứ không
    phải từng ticker riêng lẻ).
    """
    if news_df is None or news_df.empty:
        return ""

    df = news_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    cutoff = df["date"].max() - pd.Timedelta(days=days)
    df = df[df["date"] >= cutoff]

    if df.empty:
        return ""

    # Thử ticker-specific trước
    subset = df[df["keyword"] == ticker.upper()]
    # Fallback: dùng tất cả market news (aggregate)
    if subset.empty:
        subset = df

    total_articles = int(subset["article_count"].sum())
    avg_sentiment  = subset["sentiment_mean"].mean()
    sentiment_label = (
        "positive" if avg_sentiment > 0.1
        else "negative" if avg_sentiment < -0.1
        else "neutral"
    )

    daily_lines = []
    agg = (subset.groupby("date")
           .agg(sentiment_mean=("sentiment_mean", "mean"),
                article_count=("article_count", "sum"))
           .sort_index(ascending=False))
    for date, row in agg.head(5).iterrows():
        daily_lines.append(
            f"  {pd.Timestamp(date).strftime('%Y-%m-%d')}: "
            f"sentiment={row['sentiment_mean']:+.2f}, "
            f"{int(row['article_count'])} articles"
        )

    return (
        f"Vietnam market news sentiment ({days} days): {sentiment_label} "
        f"(avg={avg_sentiment:+.2f}, {total_articles} total articles)\n"
        + "\n".join(daily_lines)
    )


def build_summary_prompt(name: str, df: pd.DataFrame,
                         news_df: pd.DataFrame | None = None) -> str:
    close       = df["close"]
    last        = close.iloc[-1]
    start       = close.iloc[0]
    change_pct  = (last - start) / start * 100
    recent_30   = df.last("30D")
    ret_30      = ((recent_30["close"].iloc[-1] - recent_30["close"].iloc[0])
                   / recent_30["close"].iloc[0] * 100) if len(recent_30) >= 2 else None
    vol         = df["volatility_30"].iloc[-1]  if "volatility_30" in df.columns else None
    ma7         = df["ma_7"].iloc[-1]            if "ma_7"          in df.columns else None
    ma30        = df["ma_30"].iloc[-1]           if "ma_30"         in df.columns else None
    bb_upper    = df["bb_upper"].iloc[-1]        if "bb_upper"      in df.columns else None
    bb_lower    = df["bb_lower"].iloc[-1]        if "bb_lower"      in df.columns else None
    outliers    = int(df["is_outlier"].sum())    if "is_outlier"    in df.columns else 0

    ticker = name.replace("stock_", "").upper()
    news_section = build_news_context(ticker, news_df) if news_df is not None else ""
    news_block = f"\nNews Sentiment:\n{news_section}" if news_section else ""

    stats = f"""Asset: {name}
Period: {df.index[0].date()} to {df.index[-1].date()}
Starting price: {_fmt(start, '.2f')}
Current price: {_fmt(last, '.2f')}
Period return: {_fmt(change_pct, '+.2f')}%
30-day return: {_fmt(ret_30, '+.2f')}%
MA 7-day: {_fmt(ma7, '.2f')}
MA 30-day: {_fmt(ma30, '.2f')}
Trend signal: {'BULLISH (MA7 > MA30)' if ma7 and ma30 and not pd.isna(ma7) and not pd.isna(ma30) and ma7 > ma30 else 'BEARISH (MA7 < MA30)'}
BB Upper: {_fmt(bb_upper, '.2f')}
BB Lower: {_fmt(bb_lower, '.2f')}
30-day annualised volatility: {_fmt(vol, '.2%')}
Anomalous sessions flagged: {outliers}{news_block}"""

    news_instruction = (
        "\n4. News sentiment alignment — does recent news support or contradict the price trend"
        if news_section else ""
    )

    return f"""You are a financial analyst. Based on the following data, write a focused 3-paragraph analysis covering:
1. Current trend and recent performance (reference specific numbers)
2. Notable anomalies or events ({outliers} flagged sessions)
3. Risk commentary based on volatility and Bollinger Band position{news_instruction}

{stats}

Be concise, data-driven, and reference the exact numbers above."""


def build_comparison_prompt(frames: dict[str, pd.DataFrame]) -> str:
    lines = []
    for name, df in frames.items():
        if "close" not in df.columns:
            continue
        ret_full = (df["close"].iloc[-1] - df["close"].iloc[0]) / df["close"].iloc[0] * 100
        recent   = df.last("30D")
        ret_30   = ((recent["close"].iloc[-1] - recent["close"].iloc[0])
                    / recent["close"].iloc[0] * 100) if len(recent) >= 2 else None
        vol      = df["volatility_30"].iloc[-1] if "volatility_30" in df.columns else None
        ticker   = name.replace("stock_", "").upper()
        lines.append(
            f"- {ticker}: full-period return={_fmt(ret_full, '+.2f')}%, "
            f"30d return={_fmt(ret_30, '+.2f')}%, "
            f"volatility={_fmt(vol, '.2%')}"
        )

    data_block = "\n".join(lines)
    return f"""Compare the following Vietnamese stocks based on performance and risk:

{data_block}

Write 2 paragraphs:
1. Relative performance — which stocks outperformed and which lagged, with specific numbers
2. Risk-adjusted outlook — compare volatility levels and what they imply for investors

Reference the specific numbers above."""
