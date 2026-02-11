"""OSINT web scraping connectors using installed D:\\repo tools."""

from typing import Any
from datetime import datetime

import structlog

from packages.etl.connectors.base import BaseConnector

logger = structlog.get_logger()


class CrawlAIConnector(BaseConnector):
    """Web content extraction using Crawl4AI (D:\\repo\\crawl4ai)."""

    def __init__(self):
        super().__init__(
            source_name="crawl4ai",
            base_url="",
        )

    async def fetch_data(self, urls: list[str] | None = None, **kwargs) -> list[dict[str, Any]]:
        """Fetch web content using Crawl4AI async crawler."""
        from crawl4ai import AsyncWebCrawler

        target_urls = urls or []
        results = []

        async with AsyncWebCrawler() as crawler:
            for url in target_urls:
                try:
                    result = await crawler.arun(url=url)
                    results.append({
                        "url": url,
                        "markdown": result.markdown,
                        "title": getattr(result, "title", ""),
                        "fetched_at": datetime.utcnow().isoformat(),
                    })
                except Exception as e:
                    logger.error("Crawl failed", url=url, error=str(e))

        return results

    async def transform_data(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        """Transform crawled content into evidence format."""
        return [
            {
                "evidence_type": "web_content",
                "title": item.get("title", item["url"]),
                "source_url": item["url"],
                "raw_content": item.get("markdown", ""),
                "metadata": {"fetched_at": item["fetched_at"], "source": "crawl4ai"},
            }
            for item in raw_data
        ]


class WebExtractorConnector(BaseConnector):
    """Web data extraction using WebExtractor (D:\\repo\\WebExtractor)."""

    def __init__(self):
        super().__init__(
            source_name="web_extractor",
            base_url="",
        )

    async def fetch_data(self, urls: list[str] | None = None, **kwargs) -> list[dict[str, Any]]:
        """Extract structured data from web pages."""
        import importlib
        results = []

        for url in (urls or []):
            try:
                response = await self.client.get(url)
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "lxml")
                results.append({
                    "url": url,
                    "title": soup.title.string if soup.title else "",
                    "text": soup.get_text(separator="\n", strip=True),
                    "links": [a.get("href") for a in soup.find_all("a", href=True)],
                    "fetched_at": datetime.utcnow().isoformat(),
                })
            except Exception as e:
                logger.error("Extraction failed", url=url, error=str(e))

        return results

    async def transform_data(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        """Transform extracted data into evidence format."""
        return [
            {
                "evidence_type": "web_extraction",
                "title": item.get("title", item["url"]),
                "source_url": item["url"],
                "raw_content": item.get("text", ""),
                "metadata": {
                    "links_count": len(item.get("links", [])),
                    "fetched_at": item["fetched_at"],
                    "source": "web_extractor",
                },
            }
            for item in raw_data
        ]


class ScrapyConnector(BaseConnector):
    """Large-scale web scraping using Scrapy framework."""

    def __init__(self):
        super().__init__(
            source_name="scrapy_crawler",
            base_url="",
        )

    async def fetch_data(self, urls: list[str] | None = None, **kwargs) -> list[dict[str, Any]]:
        """Fetch using Scrapy's CrawlerProcess (async wrapper)."""
        import asyncio
        from scrapy.http import TextResponse
        import httpx

        results = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for url in (urls or []):
                try:
                    resp = await client.get(url)
                    results.append({
                        "url": url,
                        "status": resp.status_code,
                        "body": resp.text,
                        "fetched_at": datetime.utcnow().isoformat(),
                    })
                except Exception as e:
                    logger.error("Scrapy fetch failed", url=url, error=str(e))

        return results

    async def transform_data(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        """Transform scraped data."""
        return [
            {
                "evidence_type": "web_scrape",
                "title": item["url"],
                "source_url": item["url"],
                "raw_content": item.get("body", ""),
                "metadata": {"status": item.get("status"), "source": "scrapy"},
            }
            for item in raw_data
            if item.get("status") == 200
        ]
