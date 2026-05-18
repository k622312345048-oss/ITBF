import logging
from datetime import datetime

import pandas as pd

from analysis.llm_client import chat
from analysis.prompt_builder import build_summary_prompt, build_comparison_prompt

logger = logging.getLogger(__name__)


class Analyzer:
    def run(self, frames: dict[str, pd.DataFrame]) -> str:
        sections = [f"# FinAgent Analysis Report\n_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n"]

        # Per-asset summaries
        sections.append("## 1. Asset Summaries\n")
        for name, df in frames.items():
            if "close" not in df.columns:
                continue
            logger.info(f"Generating summary for {name}...")
            prompt = build_summary_prompt(name, df)
            try:
                response = chat(prompt)
                sections.append(f"### {name}\n{response}\n")
            except Exception as e:
                logger.error(f"LLM call failed for {name}: {e}")
                sections.append(f"### {name}\n_Analysis unavailable: {e}_\n")

        # Cross-asset comparison
        if len(frames) >= 2:
            sections.append("## 2. Comparative Analysis\n")
            logger.info("Generating cross-asset comparison...")
            try:
                prompt = build_comparison_prompt(frames)
                response = chat(prompt)
                sections.append(response + "\n")
            except Exception as e:
                logger.error(f"Comparison LLM call failed: {e}")

        return "\n".join(sections)
