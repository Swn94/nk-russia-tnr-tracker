"""Data connector for Freedom House Transnational Repression (TNR) reports."""

from typing import Any, Optional
from datetime import datetime
import re

from bs4 import BeautifulSoup

from .base import BaseConnector


class FreedomHouseConnector(BaseConnector):
    """Connector for Freedom House Transnational Repression data."""

    BASE_URL = "https://freedomhouse.org"
    TNR_REPORT_URL = "https://freedomhouse.org/report/transnational-repression"

    # TNR Type definitions based on Freedom House methodology
    TNR_TYPES = {
        "direct_attack": {
            "description": "Direct attacks including assassinations, kidnappings, assaults",
            "keywords": ["assassination", "murder", "kidnapping", "abduction", "assault", "attack", "killed"],
        },
        "co_opting": {
            "description": "Co-opting other countries through informal or formal requests",
            "keywords": ["interpol", "extradition", "deportation", "red notice", "arrest warrant", "cooperation"],
        },
        "mobility_controls": {
            "description": "Mobility controls including passport cancellations and visa denials",
            "keywords": ["passport", "visa", "travel ban", "border", "citizenship", "revocation"],
        },
        "threats_from_distance": {
            "description": "Threats from distance including surveillance, cyber attacks, targeting family",
            "keywords": ["surveillance", "monitoring", "spyware", "hacking", "family", "relatives", "threat", "intimidation"],
        },
    }

    # Countries of focus for NK-Russia project
    TARGET_COUNTRIES = ["North Korea", "DPRK", "Russia", "Russian Federation"]

    def __init__(self):
        super().__init__(
            source_name="Freedom House",
            base_url=self.BASE_URL,
        )

    async def fetch_data(
        self,
        country: Optional[str] = None,
        tnr_type: Optional[str] = None,
        year: Optional[int] = None,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """
        Fetch TNR case data from Freedom House.

        Args:
            country: Filter by origin country (e.g., "North Korea", "Russia")
            tnr_type: Filter by TNR type (direct_attack, co_opting, mobility_controls, threats_from_distance)
            year: Filter by year
        """
        cases = []

        # Fetch main TNR report page
        try:
            response = await self.get("/report/transnational-repression")
            soup = BeautifulSoup(response.text, "lxml")

            # Extract country report links
            country_links = []
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if "/report/transnational-repression/" in href and href != "/report/transnational-repression":
                    country_name = link.get_text(strip=True)
                    country_links.append({
                        "country": country_name,
                        "url": href if href.startswith("http") else f"{self.BASE_URL}{href}",
                    })

            # Filter by country if specified
            if country:
                country_lower = country.lower()
                country_links = [
                    c for c in country_links
                    if country_lower in c["country"].lower()
                ]

            # Fetch individual country pages
            for country_info in country_links[:10]:  # Limit to avoid overwhelming the server
                try:
                    country_response = await self.get(country_info["url"])
                    country_soup = BeautifulSoup(country_response.text, "lxml")

                    # Extract case information from the page
                    content = country_soup.find("article") or country_soup.find("main")
                    if content:
                        text_content = content.get_text(separator=" ", strip=True)

                        # Identify TNR types mentioned
                        detected_types = []
                        for type_key, type_info in self.TNR_TYPES.items():
                            for keyword in type_info["keywords"]:
                                if keyword.lower() in text_content.lower():
                                    detected_types.append(type_key)
                                    break

                        cases.append({
                            "country": country_info["country"],
                            "url": country_info["url"],
                            "content_preview": text_content[:2000],
                            "detected_tnr_types": list(set(detected_types)),
                            "fetch_date": datetime.utcnow().isoformat(),
                        })

                except Exception as e:
                    cases.append({
                        "country": country_info["country"],
                        "url": country_info["url"],
                        "error": str(e),
                    })

        except Exception as e:
            # Return error information
            return [{"error": str(e), "source": "Freedom House main page"}]

        return cases

    async def transform_data(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        """Transform Freedom House data into standardized format."""
        transformed = []

        for item in raw_data:
            if "error" in item and "country" not in item:
                continue

            # Skip items with errors
            if item.get("error"):
                transformed.append({
                    "type": "error",
                    "source": "Freedom House",
                    "country": item.get("country"),
                    "error": item.get("error"),
                })
                continue

            # Determine if this is a target country for our project
            is_target = any(
                target.lower() in item.get("country", "").lower()
                for target in self.TARGET_COUNTRIES
            )

            transformed.append({
                "type": "country_report",
                "source": "Freedom House",
                "source_url": item.get("url"),
                "country": item.get("country"),
                "is_target_country": is_target,
                "tnr_types_detected": item.get("detected_tnr_types", []),
                "content_preview": item.get("content_preview"),
                "fetch_date": item.get("fetch_date"),
                "raw_data": item,
            })

        return transformed

    async def fetch_north_korea_data(self) -> dict[str, Any]:
        """Fetch TNR data specifically for North Korea."""
        return await self.sync(country="North Korea")

    async def fetch_russia_data(self) -> dict[str, Any]:
        """Fetch TNR data specifically for Russia."""
        return await self.sync(country="Russia")

    def classify_tnr_type(self, text: str) -> list[str]:
        """Classify text into TNR types based on keywords."""
        detected = []
        text_lower = text.lower()

        for type_key, type_info in self.TNR_TYPES.items():
            for keyword in type_info["keywords"]:
                if keyword.lower() in text_lower:
                    detected.append(type_key)
                    break

        return list(set(detected))
