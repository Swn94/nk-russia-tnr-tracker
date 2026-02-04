"""Data connectors for international organizations (UN OHCHR, ICC, OSCE)."""

from typing import Any, Optional
from datetime import datetime

from bs4 import BeautifulSoup

from .base import BaseConnector


class UNOHCHRConnector(BaseConnector):
    """Connector for UN Office of the High Commissioner for Human Rights."""

    BASE_URL = "https://www.ohchr.org"

    def __init__(self):
        super().__init__(
            source_name="UN OHCHR",
            base_url=self.BASE_URL,
        )

    async def fetch_data(
        self,
        country: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 50,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """
        Fetch human rights data from UN OHCHR.

        Args:
            country: Filter by country (e.g., "north-korea", "russia")
            topic: Filter by topic (e.g., "torture", "detention")
            limit: Maximum results
        """
        results = []

        # Search paths for relevant content
        search_paths = []

        if country:
            country_slug = country.lower().replace(" ", "-")
            search_paths.extend([
                f"/en/countries/{country_slug}",
                f"/en/news?country={country_slug}",
            ])
        else:
            # Default searches for NK and Russia
            search_paths = [
                "/en/countries/democratic-peoples-republic-korea",
                "/en/countries/russian-federation",
                "/en/news?field_content_category_target_id=2376",  # DPRK news
            ]

        for path in search_paths:
            try:
                response = await self.get(path)
                soup = BeautifulSoup(response.text, "lxml")

                # Extract news items
                articles = soup.find_all("article") or soup.find_all("div", class_="news-item")

                for article in articles[:limit]:
                    title_elem = article.find(["h2", "h3", "h4", "a"])
                    date_elem = article.find(["time", "span"], class_=lambda x: x and "date" in x.lower() if x else False)
                    link_elem = article.find("a", href=True)

                    results.append({
                        "title": title_elem.get_text(strip=True) if title_elem else None,
                        "date": date_elem.get_text(strip=True) if date_elem else None,
                        "url": link_elem["href"] if link_elem else None,
                        "source_path": path,
                        "fetch_date": datetime.utcnow().isoformat(),
                    })

            except Exception as e:
                results.append({
                    "error": str(e),
                    "source_path": path,
                })

        return results

    async def transform_data(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        """Transform UN OHCHR data into standardized format."""
        transformed = []

        for item in raw_data:
            if item.get("error"):
                continue

            url = item.get("url", "")
            if url and not url.startswith("http"):
                url = f"{self.BASE_URL}{url}"

            transformed.append({
                "type": "news_report",
                "source": "UN OHCHR",
                "title": item.get("title"),
                "date": item.get("date"),
                "source_url": url,
                "fetch_date": item.get("fetch_date"),
                "raw_data": item,
            })

        return transformed


class ICCConnector(BaseConnector):
    """Connector for International Criminal Court."""

    BASE_URL = "https://www.icc-cpi.int"

    def __init__(self):
        super().__init__(
            source_name="ICC",
            base_url=self.BASE_URL,
        )

    async def fetch_data(
        self,
        situation: Optional[str] = None,
        case_type: Optional[str] = None,
        limit: int = 50,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """
        Fetch case data from ICC.

        Args:
            situation: Filter by situation/country
            case_type: Filter by case type
            limit: Maximum results
        """
        results = []

        # Relevant ICC pages
        search_paths = [
            "/situations-under-investigations",
            "/cases",
            "/news",
        ]

        for path in search_paths:
            try:
                response = await self.get(path)
                soup = BeautifulSoup(response.text, "lxml")

                # Extract case/situation items
                items = soup.find_all("article") or soup.find_all("div", class_=lambda x: x and ("case" in x.lower() or "situation" in x.lower()) if x else False)

                for item in items[:limit]:
                    title_elem = item.find(["h2", "h3", "h4"])
                    link_elem = item.find("a", href=True)
                    summary_elem = item.find("p")

                    results.append({
                        "title": title_elem.get_text(strip=True) if title_elem else None,
                        "url": link_elem["href"] if link_elem else None,
                        "summary": summary_elem.get_text(strip=True) if summary_elem else None,
                        "source_path": path,
                        "fetch_date": datetime.utcnow().isoformat(),
                    })

            except Exception as e:
                results.append({
                    "error": str(e),
                    "source_path": path,
                })

        return results

    async def transform_data(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        """Transform ICC data into standardized format."""
        transformed = []

        for item in raw_data:
            if item.get("error"):
                continue

            url = item.get("url", "")
            if url and not url.startswith("http"):
                url = f"{self.BASE_URL}{url}"

            transformed.append({
                "type": "icc_case",
                "source": "ICC",
                "title": item.get("title"),
                "summary": item.get("summary"),
                "source_url": url,
                "fetch_date": item.get("fetch_date"),
                "raw_data": item,
            })

        return transformed


class OSCEConnector(BaseConnector):
    """Connector for Organization for Security and Co-operation in Europe."""

    BASE_URL = "https://www.osce.org"

    def __init__(self):
        super().__init__(
            source_name="OSCE",
            base_url=self.BASE_URL,
        )

    async def fetch_data(
        self,
        topic: Optional[str] = None,
        region: Optional[str] = None,
        limit: int = 50,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """
        Fetch human rights reports from OSCE.

        Args:
            topic: Filter by topic (e.g., "human-rights", "human-dimension")
            region: Filter by region
            limit: Maximum results
        """
        results = []

        # OSCE relevant paths
        search_paths = [
            "/human-dimension",
            "/resources/reports",
            "/news?filters=theme:human-rights",
        ]

        if topic:
            search_paths.append(f"/{topic}")

        for path in search_paths:
            try:
                response = await self.get(path)
                soup = BeautifulSoup(response.text, "lxml")

                # Extract content items
                items = soup.find_all("article") or soup.find_all("div", class_="content-item")

                for item in items[:limit]:
                    title_elem = item.find(["h2", "h3", "h4"])
                    link_elem = item.find("a", href=True)
                    date_elem = item.find(["time", "span"], class_=lambda x: x and "date" in x.lower() if x else False)

                    results.append({
                        "title": title_elem.get_text(strip=True) if title_elem else None,
                        "url": link_elem["href"] if link_elem else None,
                        "date": date_elem.get_text(strip=True) if date_elem else None,
                        "source_path": path,
                        "fetch_date": datetime.utcnow().isoformat(),
                    })

            except Exception as e:
                results.append({
                    "error": str(e),
                    "source_path": path,
                })

        return results

    async def transform_data(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        """Transform OSCE data into standardized format."""
        transformed = []

        for item in raw_data:
            if item.get("error"):
                continue

            url = item.get("url", "")
            if url and not url.startswith("http"):
                url = f"{self.BASE_URL}{url}"

            transformed.append({
                "type": "osce_report",
                "source": "OSCE",
                "title": item.get("title"),
                "date": item.get("date"),
                "source_url": url,
                "fetch_date": item.get("fetch_date"),
                "raw_data": item,
            })

        return transformed
