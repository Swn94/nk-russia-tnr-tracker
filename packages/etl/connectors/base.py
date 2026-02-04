"""Base connector class for all data sources."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from packages.core.utils.config import get_settings

logger = structlog.get_logger()


class BaseConnector(ABC):
    """Abstract base class for data source connectors."""

    def __init__(self, source_name: str, base_url: str):
        self.source_name = source_name
        self.base_url = base_url
        self.settings = get_settings()
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "TNR-Tracker/0.1.0"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Connector not initialized. Use async context manager.")
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def _request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        """Make an HTTP request with retry logic."""
        logger.info(
            "Making request",
            source=self.source_name,
            method=method,
            url=url,
        )
        response = await self.client.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    async def get(self, path: str, **kwargs) -> httpx.Response:
        """Make a GET request."""
        url = f"{self.base_url}{path}" if not path.startswith("http") else path
        return await self._request("GET", url, **kwargs)

    async def post(self, path: str, **kwargs) -> httpx.Response:
        """Make a POST request."""
        url = f"{self.base_url}{path}" if not path.startswith("http") else path
        return await self._request("POST", url, **kwargs)

    @abstractmethod
    async def fetch_data(self, **kwargs) -> list[dict[str, Any]]:
        """Fetch data from the source. Must be implemented by subclasses."""
        pass

    @abstractmethod
    async def transform_data(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        """Transform raw data into standardized format."""
        pass

    async def sync(self, **kwargs) -> dict[str, Any]:
        """Full sync operation: fetch and transform data."""
        start_time = datetime.utcnow()
        logger.info("Starting sync", source=self.source_name)

        try:
            raw_data = await self.fetch_data(**kwargs)
            transformed = await self.transform_data(raw_data)

            elapsed = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                "Sync completed",
                source=self.source_name,
                records=len(transformed),
                elapsed_seconds=elapsed,
            )

            return {
                "source": self.source_name,
                "status": "success",
                "records_fetched": len(raw_data),
                "records_transformed": len(transformed),
                "data": transformed,
                "elapsed_seconds": elapsed,
            }

        except Exception as e:
            logger.error(
                "Sync failed",
                source=self.source_name,
                error=str(e),
            )
            return {
                "source": self.source_name,
                "status": "error",
                "error": str(e),
            }
