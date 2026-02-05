"""TJWG FOOTPRINTS API endpoints.

Provides access to FOOTPRINTS database records (victims, perpetrators, proceedings)
and mapping services to connect with data.go.kr statistics.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

from packages.core.models.footprints import (
    FootprintsVictim,
    FootprintsPerpetrator,
    FootprintsProceeding,
    FootprintsVictimType,
    FootprintsPerpOrganization,
    FootprintsSearchParams,
    FootprintsSyncStatus,
)
from packages.core.utils.db import get_db
from packages.etl.connectors import TJWGFootprintsConnector

router = APIRouter()


# =============================================================================
# VICTIMS ENDPOINTS
# =============================================================================

@router.get("/victims", response_model=list[dict])
async def list_victims(
    victim_type: Optional[FootprintsVictimType] = None,
    nationality: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """
    List FOOTPRINTS victim records.

    - **victim_type**: Filter by victim classification (abductee, pow, defector, etc.)
    - **nationality**: Filter by nationality
    - **year_from/year_to**: Filter by incident year range
    - **search**: Full-text search in name fields
    """
    db = await get_db()

    query = "SELECT * FROM footprints_victims WHERE 1=1"
    params = []
    param_idx = 1

    if victim_type:
        query += f" AND victim_type = ${param_idx}::footprints_victim_type"
        params.append(victim_type.value)
        param_idx += 1

    if nationality:
        query += f" AND nationality ILIKE ${param_idx}"
        params.append(f"%{nationality}%")
        param_idx += 1

    if year_from:
        query += f" AND EXTRACT(YEAR FROM date_of_incident) >= ${param_idx}"
        params.append(year_from)
        param_idx += 1

    if year_to:
        query += f" AND EXTRACT(YEAR FROM date_of_incident) <= ${param_idx}"
        params.append(year_to)
        param_idx += 1

    if search:
        query += f" AND (name ILIKE ${param_idx} OR name_korean ILIKE ${param_idx})"
        params.append(f"%{search}%")
        param_idx += 1

    query += f" ORDER BY date_of_incident DESC NULLS LAST LIMIT ${param_idx} OFFSET ${param_idx + 1}"
    params.extend([limit, offset])

    rows = await db.fetch(query, *params)
    return [dict(row) for row in rows]


@router.get("/victims/{victim_id}")
async def get_victim(victim_id: UUID):
    """Get a specific FOOTPRINTS victim record."""
    db = await get_db()

    row = await db.fetchrow(
        "SELECT * FROM footprints_victims WHERE id = $1",
        victim_id,
    )

    if not row:
        raise HTTPException(status_code=404, detail="Victim not found")

    return dict(row)


@router.get("/victims/{victim_id}/context")
async def get_victim_statistical_context(victim_id: UUID):
    """
    Get statistical context for a victim.

    Returns aggregate statistics from data.go.kr that provide context
    for this individual case.
    """
    from packages.etl.mapping import FootprintsDataMapper

    mapper = FootprintsDataMapper()
    await mapper.initialize()

    context = await mapper.get_statistical_context(victim_id)
    return context


@router.post("/victims/{victim_id}/link-actor")
async def link_victim_to_actor(victim_id: UUID):
    """
    Link a FOOTPRINTS victim to the main actors table.

    Creates a unified actor record for cross-source tracking.
    """
    from packages.etl.mapping import FootprintsDataMapper

    mapper = FootprintsDataMapper()
    await mapper.initialize()

    result = await mapper.link_to_actor(victim_id, actor_type="victim")
    return result


# =============================================================================
# PERPETRATORS ENDPOINTS
# =============================================================================

@router.get("/perpetrators", response_model=list[dict])
async def list_perpetrators(
    organization: Optional[FootprintsPerpOrganization] = None,
    perpetrator_type: Optional[str] = None,
    sanctioned: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """
    List FOOTPRINTS perpetrator records.

    - **organization**: Filter by organization (mss, mps, kpa, party)
    - **perpetrator_type**: Filter by perpetrator type
    - **sanctioned**: Filter by sanction status
    - **search**: Full-text search in name fields
    """
    db = await get_db()

    query = "SELECT * FROM footprints_perpetrators WHERE 1=1"
    params = []
    param_idx = 1

    if organization:
        query += f" AND organization = ${param_idx}::footprints_perp_organization"
        params.append(organization.value)
        param_idx += 1

    if perpetrator_type:
        query += f" AND perpetrator_type = ${param_idx}::footprints_perpetrator_type"
        params.append(perpetrator_type)
        param_idx += 1

    if sanctioned is not None:
        query += f" AND sanctioned = ${param_idx}"
        params.append(sanctioned)
        param_idx += 1

    if search:
        query += f" AND (name ILIKE ${param_idx} OR name_korean ILIKE ${param_idx})"
        params.append(f"%{search}%")
        param_idx += 1

    query += f" ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
    params.extend([limit, offset])

    rows = await db.fetch(query, *params)
    return [dict(row) for row in rows]


@router.get("/perpetrators/{perpetrator_id}")
async def get_perpetrator(perpetrator_id: UUID):
    """Get a specific FOOTPRINTS perpetrator record."""
    db = await get_db()

    row = await db.fetchrow(
        "SELECT * FROM footprints_perpetrators WHERE id = $1",
        perpetrator_id,
    )

    if not row:
        raise HTTPException(status_code=404, detail="Perpetrator not found")

    return dict(row)


@router.post("/perpetrators/{perpetrator_id}/link-actor")
async def link_perpetrator_to_actor(perpetrator_id: UUID):
    """Link a FOOTPRINTS perpetrator to the main actors table."""
    from packages.etl.mapping import FootprintsPerpMapper

    mapper = FootprintsPerpMapper()
    await mapper.initialize()

    result = await mapper.link_perpetrator_to_actor(perpetrator_id)
    return result


# =============================================================================
# PROCEEDINGS ENDPOINTS
# =============================================================================

@router.get("/proceedings", response_model=list[dict])
async def list_proceedings(
    forum: Optional[str] = None,
    proceeding_type: Optional[str] = None,
    status: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """
    List FOOTPRINTS legal proceeding records.

    - **forum**: Filter by legal forum (un_hrc, un_ga, icc, etc.)
    - **proceeding_type**: Filter by proceeding type
    - **status**: Filter by status
    """
    db = await get_db()

    query = "SELECT * FROM footprints_proceedings WHERE 1=1"
    params = []
    param_idx = 1

    if forum:
        query += f" AND forum = ${param_idx}::footprints_proceeding_forum"
        params.append(forum)
        param_idx += 1

    if proceeding_type:
        query += f" AND proceeding_type = ${param_idx}::footprints_proceeding_type"
        params.append(proceeding_type)
        param_idx += 1

    if status:
        query += f" AND status ILIKE ${param_idx}"
        params.append(f"%{status}%")
        param_idx += 1

    if year_from:
        query += f" AND EXTRACT(YEAR FROM date_initiated) >= ${param_idx}"
        params.append(year_from)
        param_idx += 1

    if year_to:
        query += f" AND EXTRACT(YEAR FROM date_initiated) <= ${param_idx}"
        params.append(year_to)
        param_idx += 1

    query += f" ORDER BY date_initiated DESC NULLS LAST LIMIT ${param_idx} OFFSET ${param_idx + 1}"
    params.extend([limit, offset])

    rows = await db.fetch(query, *params)
    return [dict(row) for row in rows]


@router.get("/proceedings/{proceeding_id}")
async def get_proceeding(proceeding_id: UUID):
    """Get a specific FOOTPRINTS proceeding record."""
    db = await get_db()

    row = await db.fetchrow(
        "SELECT * FROM footprints_proceedings WHERE id = $1",
        proceeding_id,
    )

    if not row:
        raise HTTPException(status_code=404, detail="Proceeding not found")

    return dict(row)


# =============================================================================
# STATISTICS & SYNC ENDPOINTS
# =============================================================================

@router.get("/stats")
async def get_footprints_stats():
    """Get FOOTPRINTS database statistics."""
    db = await get_db()

    stats = {}

    # Count victims by type
    victim_stats = await db.fetch(
        """
        SELECT victim_type, COUNT(*) as count
        FROM footprints_victims
        GROUP BY victim_type
        ORDER BY count DESC
        """
    )
    stats["victims_by_type"] = {row["victim_type"]: row["count"] for row in victim_stats}

    # Count perpetrators by organization
    perp_stats = await db.fetch(
        """
        SELECT organization, COUNT(*) as count
        FROM footprints_perpetrators
        WHERE organization IS NOT NULL
        GROUP BY organization
        ORDER BY count DESC
        """
    )
    stats["perpetrators_by_org"] = {str(row["organization"]): row["count"] for row in perp_stats}

    # Count proceedings by forum
    proc_stats = await db.fetch(
        """
        SELECT forum, COUNT(*) as count
        FROM footprints_proceedings
        WHERE forum IS NOT NULL
        GROUP BY forum
        ORDER BY count DESC
        """
    )
    stats["proceedings_by_forum"] = {str(row["forum"]): row["count"] for row in proc_stats}

    # Totals
    stats["totals"] = {
        "victims": await db.fetchval("SELECT COUNT(*) FROM footprints_victims"),
        "perpetrators": await db.fetchval("SELECT COUNT(*) FROM footprints_perpetrators"),
        "proceedings": await db.fetchval("SELECT COUNT(*) FROM footprints_proceedings"),
        "linked_victims": await db.fetchval(
            "SELECT COUNT(*) FROM footprints_victims WHERE linked_actor_id IS NOT NULL"
        ),
        "linked_perpetrators": await db.fetchval(
            "SELECT COUNT(*) FROM footprints_perpetrators WHERE linked_actor_id IS NOT NULL"
        ),
    }

    # Last sync
    last_sync = await db.fetchrow(
        "SELECT * FROM footprints_sync_status ORDER BY last_sync_at DESC LIMIT 1"
    )
    if last_sync:
        stats["last_sync"] = {
            "at": last_sync["last_sync_at"].isoformat() if last_sync["last_sync_at"] else None,
            "status": last_sync["status"],
            "victims_synced": last_sync["victims_synced"],
            "perpetrators_synced": last_sync["perpetrators_synced"],
            "proceedings_synced": last_sync["proceedings_synced"],
        }

    return stats


@router.post("/sync")
async def trigger_footprints_sync(background_tasks: BackgroundTasks):
    """
    Trigger a synchronization with TJWG FOOTPRINTS database.

    This runs in the background and fetches the latest data from
    the FOOTPRINTS API.
    """
    from packages.etl.pipeline import ETLPipeline

    async def run_sync():
        pipeline = ETLPipeline()
        await pipeline.run_connector("tjwg_footprints")

    background_tasks.add_task(run_sync)

    return {
        "status": "sync_started",
        "message": "FOOTPRINTS sync initiated in background",
    }


@router.post("/mapping/auto-map")
async def auto_map_victims_to_statistics(
    limit: int = Query(default=100, ge=1, le=1000),
    min_confidence: float = Query(default=0.3, ge=0, le=1),
):
    """
    Automatically map FOOTPRINTS victims to statistical context.

    Creates mappings between individual victim records and aggregate
    statistics from data.go.kr based on available demographic data.
    """
    from packages.etl.mapping import FootprintsDataMapper

    mapper = FootprintsDataMapper()
    await mapper.initialize()

    result = await mapper.auto_map_victims(
        limit=limit,
        min_confidence=min_confidence,
    )

    return result


# =============================================================================
# CROSS-REFERENCE ENDPOINTS
# =============================================================================

@router.get("/crossref/defector-stats")
async def get_defector_stats_crossref():
    """
    Get cross-referenced view of FOOTPRINTS victims with defector statistics.

    Returns victims along with their statistical context from data.go.kr.
    """
    db = await get_db()

    rows = await db.fetch(
        """
        SELECT
            fv.id,
            fv.external_id,
            fv.name,
            fv.name_korean,
            fv.victim_type,
            fv.date_of_incident,
            EXTRACT(YEAR FROM fv.date_of_incident) AS incident_year,
            fv.age_at_incident,
            fv.occupation,
            fv.place_of_incident,
            dcm.arrival_year,
            dcm.age_group,
            dcm.mapping_confidence,
            dsy.total AS year_total,
            dsy.male AS year_male,
            dsy.female AS year_female
        FROM footprints_victims fv
        LEFT JOIN defector_case_mapping dcm ON fv.id = dcm.footprints_victim_id
        LEFT JOIN defector_stats_yearly dsy ON dcm.arrival_year = dsy.year
        WHERE fv.victim_type IN ('defector', 'detained', 'disappeared')
        ORDER BY fv.date_of_incident DESC NULLS LAST
        LIMIT 100
        """
    )

    return [dict(row) for row in rows]
