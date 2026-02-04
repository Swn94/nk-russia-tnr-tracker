"""Data connector for data.go.kr (Korean government open data) - North Korean defector statistics."""

from typing import Any
from datetime import date

from .base import BaseConnector
from packages.core.utils.config import get_settings


class DataGoKrConnector(BaseConnector):
    """Connector for 통일부 북한이탈주민 API (Ministry of Unification NK Defector API)."""

    API_KEY = "55620ffd8bd0d266e4981c0d47122317349e75f35cc7b855ada3b9f0453f1c4e"
    BASE_URL = "https://apis.data.go.kr/1250000/prsn"

    def __init__(self):
        super().__init__(
            source_name="data.go.kr",
            base_url=self.BASE_URL,
        )
        self.api_key = get_settings().data_go_kr_api_key or self.API_KEY

    async def fetch_data(
        self,
        service_key: str = None,
        page_no: int = 1,
        num_of_rows: int = 100,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """
        Fetch North Korean defector statistics from data.go.kr.

        Available endpoints:
        - /getPrsnYear: 연도별 북한이탈주민 입국현황
        - /getPrsnAge: 연령별 북한이탈주민 현황
        - /getPrsnOccup: 직업별 북한이탈주민 현황
        - /getPrsnArea: 출신지역별 북한이탈주민 현황
        """
        all_data = []
        endpoints = [
            "/getPrsnYear",
            "/getPrsnAge",
            "/getPrsnOccup",
            "/getPrsnArea",
        ]

        for endpoint in endpoints:
            try:
                params = {
                    "serviceKey": service_key or self.api_key,
                    "pageNo": page_no,
                    "numOfRows": num_of_rows,
                    "type": "json",
                }

                response = await self.get(endpoint, params=params)
                data = response.json()

                # Handle different response structures
                if "response" in data:
                    body = data.get("response", {}).get("body", {})
                    items = body.get("items", {})
                    if isinstance(items, dict):
                        item_list = items.get("item", [])
                    else:
                        item_list = items if isinstance(items, list) else []

                    for item in item_list if isinstance(item_list, list) else [item_list]:
                        item["_endpoint"] = endpoint
                        all_data.append(item)

            except Exception as e:
                # Log error but continue with other endpoints
                all_data.append({
                    "_endpoint": endpoint,
                    "_error": str(e),
                })

        return all_data

    async def transform_data(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        """Transform raw API data into standardized case/evidence format."""
        transformed = []

        for item in raw_data:
            if "_error" in item:
                continue

            endpoint = item.get("_endpoint", "")

            # Transform based on endpoint type
            if "Year" in endpoint:
                # 연도별 데이터
                transformed.append({
                    "type": "statistics",
                    "category": "yearly_defector_count",
                    "year": item.get("yyyy"),
                    "total": item.get("total"),
                    "male": item.get("male"),
                    "female": item.get("female"),
                    "source": "data.go.kr",
                    "source_endpoint": endpoint,
                    "raw_data": item,
                })
            elif "Age" in endpoint:
                # 연령별 데이터
                transformed.append({
                    "type": "statistics",
                    "category": "age_distribution",
                    "age_group": item.get("age"),
                    "count": item.get("cnt"),
                    "source": "data.go.kr",
                    "source_endpoint": endpoint,
                    "raw_data": item,
                })
            elif "Occup" in endpoint:
                # 직업별 데이터
                transformed.append({
                    "type": "statistics",
                    "category": "occupation_distribution",
                    "occupation": item.get("occup"),
                    "count": item.get("cnt"),
                    "source": "data.go.kr",
                    "source_endpoint": endpoint,
                    "raw_data": item,
                })
            elif "Area" in endpoint:
                # 출신지역별 데이터
                transformed.append({
                    "type": "statistics",
                    "category": "origin_region",
                    "region": item.get("area"),
                    "count": item.get("cnt"),
                    "source": "data.go.kr",
                    "source_endpoint": endpoint,
                    "raw_data": item,
                })

        return transformed

    async def fetch_defector_statistics(self) -> dict[str, Any]:
        """Convenience method to get all defector statistics."""
        result = await self.sync()
        if result["status"] == "success":
            # Organize by category
            organized = {
                "yearly": [],
                "by_age": [],
                "by_occupation": [],
                "by_region": [],
            }
            for item in result["data"]:
                category = item.get("category", "")
                if "yearly" in category:
                    organized["yearly"].append(item)
                elif "age" in category:
                    organized["by_age"].append(item)
                elif "occupation" in category:
                    organized["by_occupation"].append(item)
                elif "region" in category:
                    organized["by_region"].append(item)

            result["organized_data"] = organized

        return result
