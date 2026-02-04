"""Data connector for HUDOC (European Court of Human Rights database)."""

from typing import Any, Optional
from datetime import datetime
import json

from bs4 import BeautifulSoup

from .base import BaseConnector


class HUDOCConnector(BaseConnector):
    """Connector for HUDOC - European Court of Human Rights case law database."""

    BASE_URL = "https://hudoc.echr.coe.int"
    SEARCH_URL = "https://hudoc.echr.coe.int/app/query/results"

    def __init__(self):
        super().__init__(
            source_name="HUDOC",
            base_url=self.BASE_URL,
        )

    async def fetch_data(
        self,
        query: Optional[str] = None,
        respondent_state: Optional[str] = None,
        article: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """
        Search HUDOC for cases.

        Args:
            query: Full-text search query
            respondent_state: Filter by respondent state (e.g., "RUS" for Russia, "UKR" for Ukraine)
            article: Filter by Convention article (e.g., "2" for right to life, "3" for torture)
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            limit: Maximum number of results
        """
        # Build HUDOC query
        query_parts = []

        if query:
            query_parts.append(f'fulltext:"{query}"')

        if respondent_state:
            query_parts.append(f'respondent:"{respondent_state}"')

        if article:
            query_parts.append(f'article:"{article}"')

        if start_date:
            query_parts.append(f'judgmentdate>="{start_date}"')

        if end_date:
            query_parts.append(f'judgmentdate<="{end_date}"')

        # Default to Russia/Ukraine related cases if no query specified
        if not query_parts:
            query_parts = ['respondent:"RUS" OR respondent:"UKR"']

        search_query = " AND ".join(query_parts) if len(query_parts) > 1 else query_parts[0]

        params = {
            "query": search_query,
            "select": "itemid,docname,applicability,appno,conclusion,doctype,doctypebranch,"
                      "ecli,importance,judgmentdate,languageisocode,meetingnumber,"
                      "originatingbody,publishedby,Rank,referencedate,reportdate,"
                      "representedby,respondent,respondentOrderEng,rulesofcourt,"
                      "separateopinion,typedescription,violation,nonviolation",
            "sort": "judgmentdate Descending",
            "start": 0,
            "length": limit,
            "rankingModelId": "11111111-0000-0000-0000-000000000000",
        }

        try:
            response = await self.get(self.SEARCH_URL, params=params)
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            # Return empty list on error, actual error logged in base class
            return []

    async def transform_data(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        """Transform HUDOC cases into standardized format."""
        transformed = []

        for item in raw_data:
            columns = item.get("columns", {})

            # Parse judgment date
            judgment_date = None
            if columns.get("judgmentdate"):
                try:
                    judgment_date = datetime.strptime(
                        columns["judgmentdate"], "%m/%d/%Y %H:%M:%S %p"
                    ).date().isoformat()
                except (ValueError, TypeError):
                    judgment_date = columns.get("judgmentdate")

            # Extract violations
            violations = []
            if columns.get("violation"):
                violations = [v.strip() for v in columns["violation"].split(";")]

            # Determine TNR type based on articles violated
            tnr_type = None
            violation_text = " ".join(violations).lower()
            if "article 2" in violation_text or "right to life" in violation_text:
                tnr_type = "direct_attack"
            elif "article 3" in violation_text or "torture" in violation_text:
                tnr_type = "direct_attack"
            elif "article 5" in violation_text or "liberty" in violation_text:
                tnr_type = "mobility_controls"
            elif "article 8" in violation_text or "private" in violation_text:
                tnr_type = "threats_from_distance"

            transformed.append({
                "type": "case",
                "source": "HUDOC",
                "case_number": columns.get("appno"),
                "title": columns.get("docname"),
                "ecli": columns.get("ecli"),
                "respondent_state": columns.get("respondent"),
                "judgment_date": judgment_date,
                "importance_level": columns.get("importance"),
                "violations": violations,
                "non_violations": columns.get("nonviolation", "").split(";") if columns.get("nonviolation") else [],
                "conclusion": columns.get("conclusion"),
                "originating_body": columns.get("originatingbody"),
                "tnr_type": tnr_type,
                "hudoc_item_id": item.get("itemid"),
                "document_url": f"{self.BASE_URL}/eng?i={item.get('itemid')}" if item.get("itemid") else None,
                "raw_data": item,
            })

        return transformed

    async def fetch_russia_cases(self, limit: int = 50) -> dict[str, Any]:
        """Fetch cases with Russia as respondent state."""
        return await self.sync(respondent_state="RUS", limit=limit)

    async def fetch_ukraine_cases(self, limit: int = 50) -> dict[str, Any]:
        """Fetch cases with Ukraine as respondent state."""
        return await self.sync(respondent_state="UKR", limit=limit)

    async def fetch_torture_cases(self, limit: int = 50) -> dict[str, Any]:
        """Fetch cases involving Article 3 (torture/inhuman treatment)."""
        return await self.sync(article="3", limit=limit)

    async def fetch_right_to_life_cases(self, limit: int = 50) -> dict[str, Any]:
        """Fetch cases involving Article 2 (right to life)."""
        return await self.sync(article="2", limit=limit)
