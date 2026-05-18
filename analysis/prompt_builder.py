import pandas as pd


def build_summary_prompt(name: str, df: pd.DataFrame) -> str:
    last = df["close"].iloc[-1]
    start = df["close"].iloc[0]
    change_pct = (last - start) / start * 100
    vol = df.get("volatility_30", pd.Series()).iloc[-1] if "volatility_30" in df.columns else None
    ma7 = df["ma_7"].iloc[-1] if "ma_7" in df.columns else None
    ma30 = df["ma_30"].iloc[-1] if "ma_30" in df.columns else None

    stats = f"""Asset: {name}
Period: {df.index[0].date()} to {df.index[-1].date()}
Starting price: {start:.4f}
Current price: {last:.4f}
Period return: {change_pct:.2f}%
MA 7-day: {ma7:.4f if ma7 else 'N/A'}
MA 30-day: {ma30:.4f if ma30 else 'N/A'}
30-day annualised volatility: {f'{vol:.2%}' if vol else 'N/A'}
"""
    return f"""Based on the following financial data, write a 2-3 paragraph summary covering:
1. Current trend and recent performance
2. Any notable anomalies or events
3. Risk commentary based on volatility

{stats}
Be specific — reference the exact numbers provided."""


def build_comparison_prompt(frames: dict[str, pd.DataFrame]) -> str:
    lines = []
    for name, df in frames.items():
        if "close" not in df.columns:
            continue
        ret = (df["close"].iloc[-1] - df["close"].iloc[0]) / df["close"].iloc[0] * 100
        vol = df["volatility_30"].iloc[-1] if "volatility_30" in df.columns else None
        lines.append(f"- {name}: return={ret:.2f}%, volatility={f'{vol:.2%}' if vol else 'N/A'}")

    data_block = "\n".join(lines)
    return f"""Compare the following assets based on their performance and risk metrics:

{data_block}

Write a 2-paragraph comparison covering relative performance and risk-adjusted outlook.
Reference the specific numbers above."""
