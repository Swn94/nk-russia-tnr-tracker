"""Data connector for TJWG FOOTPRINTS (NK Footprints 2.0) database.

TJWG FOOTPRINTS is a joint civil society project documenting:
- Arbitrary detention
- Abduction
- Enforced disappearances
committed in and by North Korea.

Built on UWAZI platform (HURIDOCS).
Source: https://nkfootprints.tjwg.org/en/library
"""

from typing import Any, Optional
from datetime import datetime
from enum import Enum

from bs4 import BeautifulSoup
import structlog

from .base import BaseConnector

logger = structlog.get_logger()


class FootprintsEntityType(str, Enum):
    """Entity types in FOOTPRINTS database."""
    VICTIM = "victim"
    PERPETRATOR = "perpetrator"
    PROCEEDING = "proceeding"
    TESTIMONIAL = "testimonial"
    HR_INSTRUMENT = "hr_instrument"
    NK_RESOURCE = "nk_resource"


class FootprintsVictimType(str, Enum):
    """Victim classification types in FOOTPRINTS."""
    ABDUCTEE = "abductee"
    POW = "pow"  # Prisoner of War
    DEFECTOR = "defector"
    DETAINED = "detained"
    DISAPPEARED = "disappeared"
    OTHER = "other"


class TJWGFootprintsConnector(BaseConnector):
    """Connector for TJWG FOOTPRINTS (NK Footprints 2.0) UWAZI database.

    This connector interfaces with the FOOTPRINTS database which documents
    cases of arbitrary detention, abduction, and enforced disappearances
    committed by North Korea.

    The database is built on UWAZI platform and provides:
    - Victim records (abductees, POWs, defectors, detained individuals)
    - Perpetrator records (state organs, officials)
    - Proceedings (legal actions, investigations)
    - Testimonials (witness accounts)
    - Human rights instruments (treaties, resolutions)
    - NK resources (official documents, reports)

    API Endpoints (UWAZI standard):
    - /api/search - Search entities with filters
    - /api/entities - Get specific entities by sharedId
    - /api/templates - Get entity templates/schemas
    - /api/settings - Get database settings
    - /api/thesauris - Get thesaurus/taxonomy data
    """

    # Primary endpoint - TJWG FOOTPRINTS 2.0
    BASE_URL = "https://nkfootprints.tjwg.org"
    # Fallback endpoint - Original FOOTPRINTS
    FALLBACK_URL = "https://nkfootprints.info"

    # UWAZI API paths
    API_SEARCH = "/api/search"
    API_ENTITIES = "/api/entities"
    API_TEMPLATES = "/api/templates"
    API_SETTINGS = "/api/settings"
    API_THESAURIS = "/api/thesauris"

    # Known template IDs for FOOTPRINTS entities (to be populated from API)
    TEMPLATE_IDS = {
        "victim": None,
        "perpetrator": None,
        "proceeding": None,
        "testimonial": None,
    }

    def __init__(self, use_fallback: bool = False):
        """Initialize TJWG FOOTPRINTS connector.

        Args:
            use_fallback: Use fallback URL (nkfootprints.info) if primary fails
        """
        base_url = self.FALLBACK_URL if use_fallback else self.BASE_URL
        super().__init__(
            source_name="TJWG FOOTPRINTS",
            base_url=base_url,
        )
        self.use_fallback = use_fallback
        self._templates_cache: Optional[list[dict]] = None
        self._settings_cache: Optional[dict] = None

    async def _get_with_fallback(self, path: str, **kwargs) -> Any:
        """Attempt request with fallback to alternate URL."""
        try:
            return await self.get(path, **kwargs)
        except Exception as e:
            if not self.use_fallback:
                logger.warning(
                    "Primary URL failed, attempting fallback",
                    error=str(e),
                    path=path,
                )
                self.base_url = self.FALLBACK_URL
                self.use_fallback = True
                return await self.get(path, **kwargs)
            raise

    async def fetch_templates(self) -> list[dict]:
        """Fetch available entity templates from UWAZI.

        Templates define the schema for different entity types
        (victim, perpetrator, proceeding, etc.)
        """
        if self._templates_cache:
            return self._templates_cache

        try:
            response = await self._get_with_fallback(self.API_TEMPLATES)
            self._templates_cache = response.json()

            # Map template names to IDs
            for template in self._templates_cache:
                name = template.get("name", "").lower()
                if "victim" in name:
                    self.TEMPLATE_IDS["victim"] = template.get("_id")
                elif "perpetrator" in name:
                    self.TEMPLATE_IDS["perpetrator"] = template.get("_id")
                elif "proceeding" in name:
                    self.TEMPLATE_IDS["proceeding"] = template.get("_id")
                elif "testimon" in name:
                    self.TEMPLATE_IDS["testimonial"] = template.get("_id")

            logger.info(
                "Fetched UWAZI templates",
                count=len(self._templates_cache),
                template_ids=self.TEMPLATE_IDS,
            )
            return self._templates_cache

        except Exception as e:
            logger.error("Failed to fetch templates", error=str(e))
            return []

    async def fetch_settings(self) -> dict:
        """Fetch UWAZI database settings."""
        if self._settings_cache:
            return self._settings_cache

        try:
            response = await self._get_with_fallback(self.API_SETTINGS)
            self._settings_cache = response.json()
            return self._settings_cache
        except Exception as e:
            logger.error("Failed to fetch settings", error=str(e))
            return {}

    async def search_entities(
        self,
        entity_type: Optional[FootprintsEntityType] = None,
        query: Optional[str] = None,
        filters: Optional[dict] = None,
        limit: int = 100,
        offset: int = 0,
        language: str = "en",
    ) -> list[dict]:
        """Search entities in FOOTPRINTS database.

        Args:
            entity_type: Filter by entity type (victim, perpetrator, etc.)
            query: Full-text search query
            filters: Additional UWAZI filters
            limit: Maximum results (default 100)
            offset: Pagination offset
            language: Language code (en, ko)

        Returns:
            List of matching entities
        """
        params = {
            "limit": limit,
            "from": offset,
        }

        if query:
            params["searchTerm"] = query

        if entity_type and self.TEMPLATE_IDS.get(entity_type.value):
            params["types"] = [self.TEMPLATE_IDS[entity_type.value]]

        if filters:
            params.update(filters)

        try:
            response = await self._get_with_fallback(
                self.API_SEARCH,
                params=params,
            )
            data = response.json()

            # UWAZI search returns {rows: [...], totalRows: n}
            rows = data.get("rows", [])
            total = data.get("totalRows", 0)

            logger.info(
                "Search completed",
                query=query,
                entity_type=entity_type.value if entity_type else None,
                returned=len(rows),
                total=total,
            )

            return rows

        except Exception as e:
            logger.error(
                "Search failed",
                error=str(e),
                query=query,
            )
            return []

    async def get_entity(self, shared_id: str) -> Optional[dict]:
        """Get a specific entity by its sharedId.

        Args:
            shared_id: UWAZI sharedId of the entity

        Returns:
            Entity data or None if not found
        """
        try:
            response = await self._get_with_fallback(
                self.API_ENTITIES,
                params={"sharedId": shared_id},
            )
            data = response.json()
            return data[0] if isinstance(data, list) and data else data

        except Exception as e:
            logger.error(
                "Failed to get entity",
                shared_id=shared_id,
                error=str(e),
            )
            return None

    async def fetch_victims(
        self,
        victim_type: Optional[FootprintsVictimType] = None,
        limit: int = 100,
        **kwargs,
    ) -> list[dict]:
        """Fetch victim records.

        Args:
            victim_type: Filter by victim classification
            limit: Maximum results
        """
        filters = {}
        if victim_type:
            filters["metadata.victim_type"] = victim_type.value

        return await self.search_entities(
            entity_type=FootprintsEntityType.VICTIM,
            filters=filters,
            limit=limit,
            **kwargs,
        )

    async def fetch_perpetrators(
        self,
        organization: Optional[str] = None,
        limit: int = 100,
        **kwargs,
    ) -> list[dict]:
        """Fetch perpetrator records.

        Args:
            organization: Filter by organization (e.g., MSS, MPS)
            limit: Maximum results
        """
        filters = {}
        if organization:
            filters["metadata.organization"] = organization

        return await self.search_entities(
            entity_type=FootprintsEntityType.PERPETRATOR,
            filters=filters,
            limit=limit,
            **kwargs,
        )

    async def fetch_proceedings(
        self,
        forum: Optional[str] = None,
        limit: int = 100,
        **kwargs,
    ) -> list[dict]:
        """Fetch legal proceeding records.

        Args:
            forum: Filter by legal forum (UN, ICC, etc.)
            limit: Maximum results
        """
        filters = {}
        if forum:
            filters["metadata.forum"] = forum

        return await self.search_entities(
            entity_type=FootprintsEntityType.PROCEEDING,
            filters=filters,
            limit=limit,
            **kwargs,
        )

    async def fetch_data(
        self,
        entity_types: Optional[list[FootprintsEntityType]] = None,
        query: Optional[str] = None,
        limit: int = 100,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """Fetch data from FOOTPRINTS database.

        Args:
            entity_types: Types of entities to fetch (default: all)
            query: Search query
            limit: Maximum results per type
        """
        results = []

        # Default to fetching all relevant types
        if entity_types is None:
            entity_types = [
                FootprintsEntityType.VICTIM,
                FootprintsEntityType.PERPETRATOR,
                FootprintsEntityType.PROCEEDING,
            ]

        # Ensure templates are loaded
        await self.fetch_templates()

        for entity_type in entity_types:
            try:
                entities = await self.search_entities(
                    entity_type=entity_type,
                    query=query,
                    limit=limit,
                )

                for entity in entities:
                    entity["_footprints_type"] = entity_type.value
                    results.append(entity)

            except Exception as e:
                logger.error(
                    "Failed to fetch entity type",
                    entity_type=entity_type.value,
                    error=str(e),
                )
                results.append({
                    "error": str(e),
                    "entity_type": entity_type.value,
                })

        return results

    async def transform_data(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        """Transform FOOTPRINTS data into standardized format.

        Maps UWAZI entity structure to internal models.
        """
        transformed = []

        for item in raw_data:
            if item.get("error"):
                continue

            entity_type = item.get("_footprints_type", "unknown")
            metadata = item.get("metadata", {})

            # Extract common fields
            base_record = {
                "source": "TJWG FOOTPRINTS",
                "source_url": f"{self.base_url}/en/entity/{item.get('sharedId', '')}",
                "external_id": item.get("sharedId"),
                "title": item.get("title"),
                "language": item.get("language", "en"),
                "created_date": item.get("creationDate"),
                "fetch_date": datetime.utcnow().isoformat(),
                "raw_data": item,
            }

            if entity_type == FootprintsEntityType.VICTIM.value:
                transformed.append(self._transform_victim(base_record, metadata))
            elif entity_type == FootprintsEntityType.PERPETRATOR.value:
                transformed.append(self._transform_perpetrator(base_record, metadata))
            elif entity_type == FootprintsEntityType.PROCEEDING.value:
                transformed.append(self._transform_proceeding(base_record, metadata))
            else:
                # Generic transformation for other types
                base_record["type"] = entity_type
                base_record["metadata"] = metadata
                transformed.append(base_record)

        return transformed

    def _transform_victim(self, base: dict, metadata: dict) -> dict:
        """Transform victim record."""
        return {
            **base,
            "type": "footprints_victim",
            "victim_type": self._extract_value(metadata.get("victim_type")),
            "name": base.get("title"),
            "name_korean": self._extract_value(metadata.get("name_korean")),
            "gender": self._extract_value(metadata.get("sex")),
            "age_at_incident": self._extract_value(metadata.get("age")),
            "occupation": self._extract_value(metadata.get("occupation")),
            "date_of_incident": self._extract_date(metadata.get("date_of_arrest")),
            "place_of_incident": self._extract_value(metadata.get("place_of_arrest")),
            "last_known_location": self._extract_value(metadata.get("last_location")),
            "status": self._extract_value(metadata.get("current_status")),
            "related_perpetrators": self._extract_relations(metadata.get("perpetrators")),
            "related_proceedings": self._extract_relations(metadata.get("proceedings")),
        }

    def _transform_perpetrator(self, base: dict, metadata: dict) -> dict:
        """Transform perpetrator record."""
        return {
            **base,
            "type": "footprints_perpetrator",
            "name": base.get("title"),
            "organization": self._extract_value(metadata.get("organization")),
            "position": self._extract_value(metadata.get("position")),
            "perpetrator_type": self._extract_value(metadata.get("perpetrator_type")),
            "period_active": self._extract_value(metadata.get("period")),
            "related_victims": self._extract_relations(metadata.get("victims")),
            "related_cases": self._extract_relations(metadata.get("cases")),
        }

    def _transform_proceeding(self, base: dict, metadata: dict) -> dict:
        """Transform proceeding record."""
        return {
            **base,
            "type": "footprints_proceeding",
            "proceeding_title": base.get("title"),
            "forum": self._extract_value(metadata.get("forum")),
            "proceeding_type": self._extract_value(metadata.get("proceeding_type")),
            "date_initiated": self._extract_date(metadata.get("date")),
            "status": self._extract_value(metadata.get("status")),
            "outcome": self._extract_value(metadata.get("outcome")),
            "related_victims": self._extract_relations(metadata.get("victims")),
            "related_perpetrators": self._extract_relations(metadata.get("perpetrators")),
            "documents": self._extract_attachments(metadata.get("documents")),
        }

    @staticmethod
    def _extract_value(field: Any) -> Optional[str]:
        """Extract value from UWAZI metadata field."""
        if field is None:
            return None
        if isinstance(field, list) and field:
            # UWAZI stores values as [{value: "..."}, ...]
            first = field[0]
            if isinstance(first, dict):
                return first.get("value") or first.get("label")
            return str(first)
        if isinstance(field, dict):
            return field.get("value") or field.get("label")
        return str(field)

    @staticmethod
    def _extract_date(field: Any) -> Optional[str]:
        """Extract date from UWAZI metadata field."""
        if field is None:
            return None
        if isinstance(field, list) and field:
            field = field[0]
        if isinstance(field, dict):
            # UWAZI dates can be timestamps or date objects
            value = field.get("value")
            if isinstance(value, (int, float)):
                return datetime.fromtimestamp(value / 1000).isoformat()
            return value
        if isinstance(field, (int, float)):
            return datetime.fromtimestamp(field / 1000).isoformat()
        return str(field)

    @staticmethod
    def _extract_relations(field: Any) -> list[str]:
        """Extract related entity IDs from UWAZI relationship field."""
        if not field:
            return []
        if not isinstance(field, list):
            field = [field]
        relations = []
        for item in field:
            if isinstance(item, dict):
                # Relations have sharedId or value
                rel_id = item.get("sharedId") or item.get("value")
                if rel_id:
                    relations.append(rel_id)
            elif isinstance(item, str):
                relations.append(item)
        return relations

    @staticmethod
    def _extract_attachments(field: Any) -> list[dict]:
        """Extract document attachments from UWAZI field."""
        if not field:
            return []
        if not isinstance(field, list):
            field = [field]
        attachments = []
        for item in field:
            if isinstance(item, dict):
                attachments.append({
                    "filename": item.get("originalname") or item.get("filename"),
                    "url": item.get("url"),
                    "mimetype": item.get("mimetype"),
                })
        return attachments

    async def fetch_library_page(self, page: int = 1, limit: int = 30) -> list[dict]:
        """Fallback: Scrape library page if API is unavailable.

        Args:
            page: Page number
            limit: Items per page
        """
        try:
            path = f"/en/library/?page={page}&limit={limit}"
            response = await self._get_with_fallback(path)
            soup = BeautifulSoup(response.text, "lxml")

            results = []

            # Try to find entity cards/items
            items = soup.find_all("div", class_=lambda x: x and "item" in x.lower() if x else False)
            if not items:
                items = soup.find_all("article")
            if not items:
                items = soup.find_all("div", class_="card")

            for item in items[:limit]:
                title_elem = item.find(["h2", "h3", "h4", "a"])
                link_elem = item.find("a", href=True)
                desc_elem = item.find("p")

                if title_elem or link_elem:
                    results.append({
                        "title": title_elem.get_text(strip=True) if title_elem else None,
                        "url": link_elem["href"] if link_elem else None,
                        "description": desc_elem.get_text(strip=True) if desc_elem else None,
                        "source_method": "web_scraping",
                        "fetch_date": datetime.utcnow().isoformat(),
                    })

            return results

        except Exception as e:
            logger.error("Library page scraping failed", error=str(e))
            return [{"error": str(e), "source_path": f"/en/library/?page={page}"}]


# Convenience function for standalone usage
async def fetch_footprints_data(
    entity_types: Optional[list[str]] = None,
    query: Optional[str] = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Standalone function to fetch FOOTPRINTS data.

    Args:
        entity_types: List of entity type names to fetch
        query: Search query
        limit: Maximum results

    Returns:
        Sync result dictionary with data
    """
    types = None
    if entity_types:
        types = [FootprintsEntityType(t) for t in entity_types]

    async with TJWGFootprintsConnector() as connector:
        return await connector.sync(
            entity_types=types,
            query=query,
            limit=limit,
        )
