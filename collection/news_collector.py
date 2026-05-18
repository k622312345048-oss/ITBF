import logging
import os
from datetime import datetime, timedelta

from newsapi import NewsApiClient

from config import settings
from collection.base_collector import BaseCollector

logger = logging.getLogger(__name__)


class NewsCollector(BaseCollector):
    """Collect financial news headlines via NewsAPI."""

    def collect(self, keywords: list[str], days_back: int = 7) -> None:
        api_key = settings.news_api_key
        if not api_key:
            logger.warning("NEWS_API_KEY not set — skipping news collection.")
            return

        client = NewsApiClient(api_key=api_key)
        from_date = (datetime.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        import pandas as pd
        articles = []

        for keyword in keywords:
            logger.info(f"Fetching news for: {keyword}")
            try:
                response = self._fetch_with_retry(
                    client.get_everything,
                    q=keyword,
                    from_param=from_date,
                    language="en",
                    sort_by="relevancy",
                    page_size=20,
                )
                for a in response.get("articles", []):
                    articles.append({
                        "keyword": keyword,
                        "published_at": a.get("publishedAt"),
                        "source": a.get("source", {}).get("name"),
                        "title": a.get("title"),
                        "description": a.get("description"),
                        "url": a.get("url"),
                    })
            except Exception as e:
                logger.error(f"News fetch failed for {keyword}: {e}")

        if articles:
            df = pd.DataFrame(articles)
            out = settings.raw_data_dir / "news.csv"
            df.to_csv(out, index=False)
            logger.info(f"Saved {len(df)} articles → {out.name}")
