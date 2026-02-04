"""Sanctions candidate-related API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from packages.core.models.evidence import (
    SanctionsCandidate,
    SanctionsCandidateCreate,
    SanctionStatus,
)
from packages.core.utils.db import get_db

router = APIRouter()


@router.get("", response_model=list[SanctionsCandidate])
async def list_candidates(
    status: Optional[SanctionStatus] = None,
    min_priority: Optional[int] = Query(default=None, ge=1, le=5),
    min_evidence_strength: Optional[float] = Query(default=None, ge=0, le=1),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """
    List sanctions candidates with optional filtering.

    - **status**: Filter by sanction status
    - **min_priority**: Minimum priority level (1-5, where 1 is highest)
    - **min_evidence_strength**: Minimum evidence strength score (0-1)
    """
    db = await get_db()

    query = "SELECT * FROM sanctions_candidates WHERE 1=1"
    params = []
    param_idx = 1

    if status:
        query += f" AND status = ${param_idx}"
        params.append(status.value)
        param_idx += 1

    if min_priority:
        query += f" AND priority_level <= ${param_idx}"  # Lower number = higher priority
        params.append(min_priority)
        param_idx += 1

    if min_evidence_strength:
        query += f" AND evidence_strength_score >= ${param_idx}"
        params.append(min_evidence_strength)
        param_idx += 1

    query += f" ORDER BY priority_level ASC NULLS LAST, evidence_strength_score DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
    params.extend([limit, offset])

    rows = await db.fetch(query, *params)
    return [dict(row) for row in rows]


@router.post("", response_model=SanctionsCandidate)
async def create_candidate(candidate: SanctionsCandidateCreate):
    """Create a new sanctions candidate."""
    db = await get_db()

    # Verify actor exists
    actor = await db.fetchrow("SELECT id FROM actors WHERE id = $1", candidate.actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")

    row = await db.fetchrow(
        """
        INSERT INTO sanctions_candidates (actor_id, status, recommendation_date,
                                         proposed_sanctions, legal_basis, supporting_cases,
                                         evidence_strength_score, priority_level,
                                         reviewing_body, decision_date, decision_notes, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        RETURNING *
        """,
        candidate.actor_id,
        candidate.status.value,
        candidate.recommendation_date,
        candidate.proposed_sanctions,
        candidate.legal_basis,
        candidate.supporting_cases,
        candidate.evidence_strength_score,
        candidate.priority_level,
        candidate.reviewing_body,
        candidate.decision_date,
        candidate.decision_notes,
        candidate.metadata,
    )

    return dict(row)


@router.get("/{candidate_id}", response_model=SanctionsCandidate)
async def get_candidate(candidate_id: UUID):
    """Get a specific sanctions candidate by ID."""
    db = await get_db()

    row = await db.fetchrow("SELECT * FROM sanctions_candidates WHERE id = $1", candidate_id)

    if not row:
        raise HTTPException(status_code=404, detail="Sanctions candidate not found")

    return dict(row)


@router.get("/{candidate_id}/full")
async def get_candidate_full(candidate_id: UUID):
    """Get full details of a sanctions candidate including actor and supporting cases."""
    db = await get_db()

    # Get candidate
    candidate = await db.fetchrow("SELECT * FROM sanctions_candidates WHERE id = $1", candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Sanctions candidate not found")

    # Get actor details
    actor = await db.fetchrow("SELECT * FROM actors WHERE id = $1", candidate["actor_id"])

    # Get supporting cases
    supporting_cases = []
    if candidate["supporting_cases"]:
        for case_id in candidate["supporting_cases"]:
            case = await db.fetchrow("SELECT * FROM cases WHERE id = $1", case_id)
            if case:
                supporting_cases.append(dict(case))

    # Get chain of command
    chain_rows = await db.fetch(
        """
        SELECT c.*, a.name as related_actor_name, a.position as related_actor_position
        FROM chain_of_command c
        JOIN actors a ON (c.superior_id = a.id OR c.subordinate_id = a.id)
        WHERE c.superior_id = $1 OR c.subordinate_id = $1
        """,
        candidate["actor_id"],
    )

    return {
        "candidate": dict(candidate),
        "actor": dict(actor) if actor else None,
        "supporting_cases": supporting_cases,
        "chain_of_command": [dict(row) for row in chain_rows],
    }


@router.patch("/{candidate_id}/status")
async def update_candidate_status(
    candidate_id: UUID,
    status: SanctionStatus,
    decision_notes: Optional[str] = None,
):
    """Update the status of a sanctions candidate."""
    db = await get_db()

    row = await db.fetchrow(
        """
        UPDATE sanctions_candidates
        SET status = $2, decision_notes = COALESCE($3, decision_notes),
            decision_date = CASE WHEN $2 IN ('sanctioned', 'rejected') THEN CURRENT_DATE ELSE decision_date END
        WHERE id = $1
        RETURNING *
        """,
        candidate_id,
        status.value,
        decision_notes,
    )

    if not row:
        raise HTTPException(status_code=404, detail="Sanctions candidate not found")

    return dict(row)


@router.delete("/{candidate_id}")
async def delete_candidate(candidate_id: UUID):
    """Delete a sanctions candidate."""
    db = await get_db()

    result = await db.execute("DELETE FROM sanctions_candidates WHERE id = $1", candidate_id)

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Sanctions candidate not found")

    return {"status": "deleted", "id": str(candidate_id)}


@router.get("/stats/overview")
async def get_candidates_overview():
    """Get overview statistics for sanctions candidates."""
    db = await get_db()

    # By status
    status_stats = await db.fetch(
        """
        SELECT status, COUNT(*) as count
        FROM sanctions_candidates
        GROUP BY status
        ORDER BY count DESC
        """
    )

    # By priority
    priority_stats = await db.fetch(
        """
        SELECT priority_level, COUNT(*) as count
        FROM sanctions_candidates
        WHERE priority_level IS NOT NULL
        GROUP BY priority_level
        ORDER BY priority_level
        """
    )

    # Average evidence strength
    avg_strength = await db.fetchval(
        "SELECT AVG(evidence_strength_score) FROM sanctions_candidates WHERE evidence_strength_score IS NOT NULL"
    )

    # Top candidates by evidence strength
    top_candidates = await db.fetch(
        """
        SELECT sc.*, a.name as actor_name
        FROM sanctions_candidates sc
        JOIN actors a ON sc.actor_id = a.id
        ORDER BY sc.evidence_strength_score DESC NULLS LAST, sc.priority_level ASC NULLS LAST
        LIMIT 10
        """
    )

    return {
        "by_status": [dict(row) for row in status_stats],
        "by_priority": [dict(row) for row in priority_stats],
        "average_evidence_strength": float(avg_strength) if avg_strength else None,
        "top_candidates": [dict(row) for row in top_candidates],
    }
