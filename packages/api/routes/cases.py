"""Case-related API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from packages.core.models.case import (
    Case,
    CaseCreate,
    CaseUpdate,
    CaseStatus,
    TNRType,
    CaseSearch,
)
from packages.core.utils.db import get_db

router = APIRouter()


@router.get("", response_model=list[Case])
async def list_cases(
    status: Optional[CaseStatus] = None,
    tnr_type: Optional[TNRType] = None,
    country: Optional[str] = None,
    min_severity: Optional[int] = Query(default=None, ge=1, le=10),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """
    List cases with optional filtering.

    - **status**: Filter by case status
    - **tnr_type**: Filter by TNR type (direct_attack, co_opting, mobility_controls, threats_from_distance)
    - **country**: Filter by country
    - **min_severity**: Minimum severity score (1-10)
    """
    db = await get_db()

    query = "SELECT * FROM cases WHERE 1=1"
    params = []
    param_idx = 1

    if status:
        query += f" AND status = ${param_idx}"
        params.append(status.value)
        param_idx += 1

    if tnr_type:
        query += f" AND tnr_type = ${param_idx}"
        params.append(tnr_type.value)
        param_idx += 1

    if country:
        query += f" AND country ILIKE ${param_idx}"
        params.append(f"%{country}%")
        param_idx += 1

    if min_severity:
        query += f" AND severity_score >= ${param_idx}"
        params.append(min_severity)
        param_idx += 1

    query += f" ORDER BY date_occurred DESC NULLS LAST, created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
    params.extend([limit, offset])

    rows = await db.fetch(query, *params)
    return [dict(row) for row in rows]


@router.post("/search", response_model=list[Case])
async def search_cases(search: CaseSearch):
    """
    Advanced case search with multiple filters.

    Supports full-text search and date range filtering.
    """
    db = await get_db()

    query = "SELECT * FROM cases WHERE 1=1"
    params = []
    param_idx = 1

    if search.query:
        query += f" AND (title ILIKE ${param_idx} OR summary ILIKE ${param_idx})"
        params.append(f"%{search.query}%")
        param_idx += 1

    if search.status:
        query += f" AND status = ${param_idx}"
        params.append(search.status.value)
        param_idx += 1

    if search.tnr_type:
        query += f" AND tnr_type = ${param_idx}"
        params.append(search.tnr_type.value)
        param_idx += 1

    if search.country:
        query += f" AND country ILIKE ${param_idx}"
        params.append(f"%{search.country}%")
        param_idx += 1

    if search.date_from:
        query += f" AND date_occurred >= ${param_idx}"
        params.append(search.date_from)
        param_idx += 1

    if search.date_to:
        query += f" AND date_occurred <= ${param_idx}"
        params.append(search.date_to)
        param_idx += 1

    if search.tags:
        query += f" AND tags && ${param_idx}"
        params.append(search.tags)
        param_idx += 1

    if search.min_severity:
        query += f" AND severity_score >= ${param_idx}"
        params.append(search.min_severity)
        param_idx += 1

    query += f" ORDER BY date_occurred DESC NULLS LAST LIMIT ${param_idx} OFFSET ${param_idx + 1}"
    params.extend([search.limit, search.offset])

    rows = await db.fetch(query, *params)
    return [dict(row) for row in rows]


@router.post("", response_model=Case)
async def create_case(case: CaseCreate):
    """Create a new case."""
    db = await get_db()

    row = await db.fetchrow(
        """
        INSERT INTO cases (title, title_korean, case_number, status, tnr_type,
                          date_occurred, date_reported, location, country,
                          summary, details, source_urls, tags, severity_score, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
        RETURNING *
        """,
        case.title,
        case.title_korean,
        case.case_number,
        case.status.value,
        case.tnr_type.value if case.tnr_type else None,
        case.date_occurred,
        case.date_reported,
        case.location,
        case.country,
        case.summary,
        case.details,
        case.source_urls,
        case.tags,
        case.severity_score,
        case.metadata,
    )

    return dict(row)


@router.get("/{case_id}", response_model=Case)
async def get_case(case_id: UUID):
    """Get a specific case by ID."""
    db = await get_db()

    row = await db.fetchrow("SELECT * FROM cases WHERE id = $1", case_id)

    if not row:
        raise HTTPException(status_code=404, detail="Case not found")

    return dict(row)


@router.patch("/{case_id}", response_model=Case)
async def update_case(case_id: UUID, update: CaseUpdate):
    """Update an existing case."""
    db = await get_db()

    updates = []
    params = []
    param_idx = 1

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            value = value.value
        elif field == "tnr_type" and value:
            value = value.value
        updates.append(f"{field} = ${param_idx}")
        params.append(value)
        param_idx += 1

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    params.append(case_id)
    query = f"UPDATE cases SET {', '.join(updates)} WHERE id = ${param_idx} RETURNING *"

    row = await db.fetchrow(query, *params)

    if not row:
        raise HTTPException(status_code=404, detail="Case not found")

    return dict(row)


@router.delete("/{case_id}")
async def delete_case(case_id: UUID):
    """Delete a case."""
    db = await get_db()

    result = await db.execute("DELETE FROM cases WHERE id = $1", case_id)

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Case not found")

    return {"status": "deleted", "id": str(case_id)}


@router.get("/{case_id}/actors")
async def get_case_actors(case_id: UUID):
    """Get all actors associated with a case."""
    db = await get_db()

    # Verify case exists
    case = await db.fetchrow("SELECT id FROM cases WHERE id = $1", case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    rows = await db.fetch(
        """
        SELECT ca.role, ca.description, a.*
        FROM case_actors ca
        JOIN actors a ON ca.actor_id = a.id
        WHERE ca.case_id = $1
        ORDER BY ca.role, a.name
        """,
        case_id,
    )

    return [dict(row) for row in rows]


@router.post("/{case_id}/actors/{actor_id}")
async def link_actor_to_case(
    case_id: UUID,
    actor_id: UUID,
    role: str = Query(..., description="Role in the case (e.g., perpetrator, victim, witness)"),
    description: Optional[str] = None,
):
    """Link an actor to a case."""
    db = await get_db()

    # Verify both exist
    case = await db.fetchrow("SELECT id FROM cases WHERE id = $1", case_id)
    actor = await db.fetchrow("SELECT id FROM actors WHERE id = $1", actor_id)

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")

    await db.execute(
        """
        INSERT INTO case_actors (case_id, actor_id, role, description)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (case_id, actor_id, role) DO UPDATE SET description = $4
        """,
        case_id,
        actor_id,
        role,
        description,
    )

    return {"status": "linked", "case_id": str(case_id), "actor_id": str(actor_id), "role": role}


@router.get("/{case_id}/evidence")
async def get_case_evidence(case_id: UUID):
    """Get all evidence for a case."""
    db = await get_db()

    rows = await db.fetch(
        """
        SELECT * FROM evidence
        WHERE case_id = $1
        ORDER BY date_obtained DESC NULLS LAST, created_at DESC
        """,
        case_id,
    )

    return [dict(row) for row in rows]


@router.get("/stats/by-tnr-type")
async def get_stats_by_tnr_type():
    """Get case statistics by TNR type."""
    db = await get_db()

    rows = await db.fetch(
        """
        SELECT tnr_type, COUNT(*) as count, AVG(severity_score) as avg_severity
        FROM cases
        WHERE tnr_type IS NOT NULL
        GROUP BY tnr_type
        ORDER BY count DESC
        """
    )

    return [dict(row) for row in rows]


@router.get("/stats/by-country")
async def get_stats_by_country():
    """Get case statistics by country."""
    db = await get_db()

    rows = await db.fetch(
        """
        SELECT country, COUNT(*) as count, AVG(severity_score) as avg_severity
        FROM cases
        WHERE country IS NOT NULL
        GROUP BY country
        ORDER BY count DESC
        LIMIT 20
        """
    )

    return [dict(row) for row in rows]
