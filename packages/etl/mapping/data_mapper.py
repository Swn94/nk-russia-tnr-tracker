"""Data mapping service for connecting TJWG FOOTPRINTS with data.go.kr statistics.

This module provides functionality to link individual case records from FOOTPRINTS
with aggregate statistics from the Korean government's defector data API.
"""

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

import structlog

from packages.core.utils.db import get_db

logger = structlog.get_logger()


class FootprintsDataMapper:
    """Maps FOOTPRINTS individual cases to aggregate statistics context."""

    # Known North Korean regions with Korean names
    NK_REGIONS = {
        "Pyongyang": "평양",
        "South Hamgyong": "함경남도",
        "North Hamgyong": "함경북도",
        "South Pyongan": "평안남도",
        "North Pyongan": "평안북도",
        "Kangwon": "강원도",
        "Hwanghae": "황해도",
        "South Hwanghae": "황해남도",
        "North Hwanghae": "황해북도",
        "Chagang": "자강도",
        "Ryanggang": "량강도",
    }

    # Age group mappings
    AGE_GROUPS = [
        (0, 9, "0-9세"),
        (10, 19, "10-19세"),
        (20, 29, "20-29세"),
        (30, 39, "30-39세"),
        (40, 49, "40-49세"),
        (50, 59, "50-59세"),
        (60, 150, "60세 이상"),
    ]

    def __init__(self):
        self.db = None

    async def initialize(self):
        """Initialize database connection."""
        self.db = await get_db()

    async def map_victim_to_statistics(
        self,
        victim_id: UUID,
        arrival_year: Optional[int] = None,
        age_at_incident: Optional[int] = None,
        occupation: Optional[str] = None,
        origin_region: Optional[str] = None,
        confidence: float = 0.5,
        method: str = "rule_based",
    ) -> dict[str, Any]:
        """
        Create a mapping between a FOOTPRINTS victim and statistical context.

        Args:
            victim_id: UUID of the FOOTPRINTS victim record
            arrival_year: Year of arrival in South Korea (if known)
            age_at_incident: Age at the time of incident
            occupation: Occupation before defection
            origin_region: Region of origin in North Korea
            confidence: Confidence score for the mapping (0-1)
            method: Mapping method used ('manual', 'rule_based', 'ml_predicted')

        Returns:
            Result dictionary with mapping details
        """
        if not self.db:
            await self.initialize()

        # Determine age group
        age_group = None
        if age_at_incident:
            for min_age, max_age, group_name in self.AGE_GROUPS:
                if min_age <= age_at_incident <= max_age:
                    age_group = group_name
                    break

        # Normalize region name
        normalized_region = self.NK_REGIONS.get(origin_region, origin_region)

        # Insert mapping
        try:
            result = await self.db.fetchrow(
                """
                INSERT INTO defector_case_mapping (
                    footprints_victim_id, arrival_year, age_group,
                    occupation, origin_region, mapping_confidence, mapping_method
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                victim_id,
                arrival_year,
                age_group,
                occupation,
                normalized_region,
                confidence,
                method,
            )

            logger.info(
                "Created victim-statistics mapping",
                victim_id=str(victim_id),
                mapping_id=str(result["id"]),
            )

            return {
                "status": "success",
                "mapping_id": result["id"],
                "victim_id": victim_id,
                "statistics_context": {
                    "year": arrival_year,
                    "age_group": age_group,
                    "occupation": occupation,
                    "region": normalized_region,
                },
            }

        except Exception as e:
            logger.error("Mapping failed", error=str(e), victim_id=str(victim_id))
            return {
                "status": "error",
                "error": str(e),
                "victim_id": victim_id,
            }

    async def auto_map_victims(
        self,
        limit: int = 100,
        min_confidence: float = 0.3,
    ) -> dict[str, Any]:
        """
        Automatically map FOOTPRINTS victims to statistics based on available data.

        This function examines FOOTPRINTS victim records and creates mappings
        to statistical context where sufficient information is available.

        Args:
            limit: Maximum number of victims to process
            min_confidence: Minimum confidence threshold for creating mappings

        Returns:
            Summary of mapping operation
        """
        if not self.db:
            await self.initialize()

        # Get unmapped victims with sufficient data
        victims = await self.db.fetch(
            """
            SELECT fv.id, fv.external_id, fv.name, fv.victim_type,
                   fv.date_of_incident, fv.age_at_incident, fv.occupation,
                   fv.place_of_incident, fv.metadata
            FROM footprints_victims fv
            LEFT JOIN defector_case_mapping dcm ON fv.id = dcm.footprints_victim_id
            WHERE dcm.id IS NULL
              AND fv.victim_type IN ('defector', 'detained', 'disappeared')
            LIMIT $1
            """,
            limit,
        )

        mapped = 0
        skipped = 0
        errors = []

        for victim in victims:
            try:
                # Extract year from date_of_incident
                arrival_year = None
                if victim["date_of_incident"]:
                    arrival_year = victim["date_of_incident"].year

                # Determine confidence based on data completeness
                confidence = 0.0
                if arrival_year:
                    confidence += 0.3
                if victim["age_at_incident"]:
                    confidence += 0.2
                if victim["occupation"]:
                    confidence += 0.2
                if victim["place_of_incident"]:
                    confidence += 0.3

                if confidence >= min_confidence:
                    result = await self.map_victim_to_statistics(
                        victim_id=victim["id"],
                        arrival_year=arrival_year,
                        age_at_incident=victim["age_at_incident"],
                        occupation=victim["occupation"],
                        origin_region=victim["place_of_incident"],
                        confidence=min(confidence, 1.0),
                        method="rule_based",
                    )

                    if result["status"] == "success":
                        mapped += 1
                    else:
                        errors.append({
                            "victim_id": str(victim["id"]),
                            "error": result.get("error"),
                        })
                else:
                    skipped += 1

            except Exception as e:
                errors.append({
                    "victim_id": str(victim["id"]),
                    "error": str(e),
                })

        return {
            "status": "completed",
            "processed": len(victims),
            "mapped": mapped,
            "skipped": skipped,
            "errors": len(errors),
            "error_details": errors[:10],  # Limit error details
        }

    async def get_statistical_context(
        self,
        victim_id: UUID,
    ) -> dict[str, Any]:
        """
        Get the statistical context for a FOOTPRINTS victim.

        Returns aggregate statistics that provide context for the individual case.
        """
        if not self.db:
            await self.initialize()

        # Get mapping
        mapping = await self.db.fetchrow(
            """
            SELECT * FROM defector_case_mapping
            WHERE footprints_victim_id = $1
            """,
            victim_id,
        )

        if not mapping:
            return {
                "status": "not_found",
                "victim_id": victim_id,
                "message": "No statistical mapping found for this victim",
            }

        context = {
            "mapping_id": mapping["id"],
            "victim_id": victim_id,
            "mapping_confidence": float(mapping["mapping_confidence"]) if mapping["mapping_confidence"] else None,
            "mapping_method": mapping["mapping_method"],
        }

        # Get yearly statistics if year is known
        if mapping["arrival_year"]:
            yearly_stats = await self.db.fetchrow(
                "SELECT * FROM defector_stats_yearly WHERE year = $1",
                mapping["arrival_year"],
            )
            if yearly_stats:
                context["yearly_context"] = {
                    "year": yearly_stats["year"],
                    "total_arrivals": yearly_stats["total"],
                    "male": yearly_stats["male"],
                    "female": yearly_stats["female"],
                }

        # Get age group statistics
        if mapping["age_group"]:
            age_stats = await self.db.fetchrow(
                "SELECT * FROM defector_stats_age WHERE age_group = $1 ORDER BY as_of_date DESC LIMIT 1",
                mapping["age_group"],
            )
            if age_stats:
                context["age_context"] = {
                    "age_group": age_stats["age_group"],
                    "count": age_stats["count"],
                    "percentage": float(age_stats["percentage"]) if age_stats["percentage"] else None,
                }

        # Get occupation statistics
        if mapping["occupation"]:
            occup_stats = await self.db.fetchrow(
                "SELECT * FROM defector_stats_occupation WHERE occupation ILIKE $1 ORDER BY as_of_date DESC LIMIT 1",
                f"%{mapping['occupation']}%",
            )
            if occup_stats:
                context["occupation_context"] = {
                    "occupation": occup_stats["occupation"],
                    "count": occup_stats["count"],
                    "percentage": float(occup_stats["percentage"]) if occup_stats["percentage"] else None,
                }

        # Get region statistics
        if mapping["origin_region"]:
            region_stats = await self.db.fetchrow(
                "SELECT * FROM defector_stats_region WHERE region ILIKE $1 ORDER BY as_of_date DESC LIMIT 1",
                f"%{mapping['origin_region']}%",
            )
            if region_stats:
                context["region_context"] = {
                    "region": region_stats["region"],
                    "count": region_stats["count"],
                    "percentage": float(region_stats["percentage"]) if region_stats["percentage"] else None,
                }

        return context

    async def link_to_actor(
        self,
        victim_id: UUID,
        actor_type: str = "victim",
    ) -> dict[str, Any]:
        """
        Create or link a FOOTPRINTS victim to the main actors table.

        This enables unified tracking across all data sources.
        """
        if not self.db:
            await self.initialize()

        # Get victim data
        victim = await self.db.fetchrow(
            "SELECT * FROM footprints_victims WHERE id = $1",
            victim_id,
        )

        if not victim:
            return {
                "status": "error",
                "error": "Victim not found",
            }

        # Check if already linked
        if victim["linked_actor_id"]:
            return {
                "status": "already_linked",
                "actor_id": victim["linked_actor_id"],
                "victim_id": victim_id,
            }

        # Create actor record
        actor_id = await self.db.fetchval(
            """
            INSERT INTO actors (name, name_korean, actor_type, nationality, description, metadata)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            victim["name"],
            victim["name_korean"],
            actor_type,
            victim["nationality"] or "North Korean",
            f"FOOTPRINTS victim: {victim['victim_type']}",
            {
                "footprints_id": victim["external_id"],
                "source": "TJWG FOOTPRINTS",
            },
        )

        # Update victim with link
        await self.db.execute(
            "UPDATE footprints_victims SET linked_actor_id = $1 WHERE id = $2",
            actor_id,
            victim_id,
        )

        logger.info(
            "Linked FOOTPRINTS victim to actor",
            victim_id=str(victim_id),
            actor_id=str(actor_id),
        )

        return {
            "status": "success",
            "actor_id": actor_id,
            "victim_id": victim_id,
        }


class FootprintsPerpMapper:
    """Maps FOOTPRINTS perpetrators to the main actors table and chain of command."""

    # Known NK government organizations
    NK_ORGANIZATIONS = {
        "MSS": {
            "name": "Ministry of State Security",
            "name_korean": "국가보위성",
            "code": "mss",
        },
        "MPS": {
            "name": "Ministry of People's Security",
            "name_korean": "사회안전성",
            "code": "mps",
        },
        "KPA": {
            "name": "Korean People's Army",
            "name_korean": "조선인민군",
            "code": "kpa",
        },
        "WPK": {
            "name": "Workers' Party of Korea",
            "name_korean": "조선로동당",
            "code": "party",
        },
    }

    def __init__(self):
        self.db = None

    async def initialize(self):
        """Initialize database connection."""
        self.db = await get_db()

    async def link_perpetrator_to_actor(
        self,
        perpetrator_id: UUID,
        actor_type: str = "perpetrator",
    ) -> dict[str, Any]:
        """
        Create or link a FOOTPRINTS perpetrator to the main actors table.
        """
        if not self.db:
            await self.initialize()

        # Get perpetrator data
        perp = await self.db.fetchrow(
            "SELECT * FROM footprints_perpetrators WHERE id = $1",
            perpetrator_id,
        )

        if not perp:
            return {
                "status": "error",
                "error": "Perpetrator not found",
            }

        if perp["linked_actor_id"]:
            return {
                "status": "already_linked",
                "actor_id": perp["linked_actor_id"],
                "perpetrator_id": perpetrator_id,
            }

        # Determine organization info
        org_info = self.NK_ORGANIZATIONS.get(
            perp["organization_name"],
            {"name": perp["organization_name"], "name_korean": None},
        )

        # Create actor record
        actor_id = await self.db.fetchval(
            """
            INSERT INTO actors (name, name_korean, actor_type, nationality, organization, position, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
            """,
            perp["name"],
            perp["name_korean"],
            actor_type,
            "North Korean",
            org_info.get("name"),
            perp["position"],
            {
                "footprints_id": perp["external_id"],
                "source": "TJWG FOOTPRINTS",
                "organization_code": org_info.get("code"),
            },
        )

        # Update perpetrator with link
        await self.db.execute(
            "UPDATE footprints_perpetrators SET linked_actor_id = $1 WHERE id = $2",
            actor_id,
            perpetrator_id,
        )

        logger.info(
            "Linked FOOTPRINTS perpetrator to actor",
            perpetrator_id=str(perpetrator_id),
            actor_id=str(actor_id),
        )

        return {
            "status": "success",
            "actor_id": actor_id,
            "perpetrator_id": perpetrator_id,
        }

    async def build_chain_of_command(
        self,
        perpetrator_ids: list[UUID],
    ) -> dict[str, Any]:
        """
        Build chain of command relationships from FOOTPRINTS perpetrator hierarchy.

        Analyzes superior_ids and subordinate_ids to create chain_of_command entries.
        """
        if not self.db:
            await self.initialize()

        created = 0
        errors = []

        for perp_id in perpetrator_ids:
            try:
                perp = await self.db.fetchrow(
                    "SELECT * FROM footprints_perpetrators WHERE id = $1",
                    perp_id,
                )

                if not perp or not perp["linked_actor_id"]:
                    continue

                # Process superior relationships
                for sup_ext_id in (perp["superior_ids"] or []):
                    sup = await self.db.fetchrow(
                        "SELECT linked_actor_id FROM footprints_perpetrators WHERE external_id = $1",
                        sup_ext_id,
                    )
                    if sup and sup["linked_actor_id"]:
                        await self.db.execute(
                            """
                            INSERT INTO chain_of_command (superior_id, subordinate_id, relationship_type, organization)
                            VALUES ($1, $2, $3, $4)
                            ON CONFLICT (superior_id, subordinate_id, organization) DO NOTHING
                            """,
                            sup["linked_actor_id"],
                            perp["linked_actor_id"],
                            "hierarchical",
                            perp["organization_name"],
                        )
                        created += 1

            except Exception as e:
                errors.append({
                    "perpetrator_id": str(perp_id),
                    "error": str(e),
                })

        return {
            "status": "completed",
            "relationships_created": created,
            "errors": len(errors),
        }
