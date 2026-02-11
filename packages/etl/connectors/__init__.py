"""Data connectors for various sources."""

from .data_go_kr_prsn import DataGoKrConnector
from .hudoc import HUDOCConnector
from .freedom_house import FreedomHouseConnector
from .international_orgs import UNOHCHRConnector, ICCConnector, OSCEConnector
from .tjwg_footprints import TJWGFootprintsConnector, FootprintsEntityType, FootprintsVictimType
from .osint_web import CrawlAIConnector, WebExtractorConnector, ScrapyConnector

__all__ = [
    "DataGoKrConnector",
    "HUDOCConnector",
    "FreedomHouseConnector",
    "UNOHCHRConnector",
    "ICCConnector",
    "OSCEConnector",
    "TJWGFootprintsConnector",
    "FootprintsEntityType",
    "FootprintsVictimType",
    "CrawlAIConnector",
    "WebExtractorConnector",
    "ScrapyConnector",
]
