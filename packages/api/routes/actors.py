"""Actor-related API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from packages.core.models.actor import (
    Actor,
    ActorCreate,
    ActorUpdate,
    ActorType,
    ChainOfCommand,
    ChainOfCommandCreate,
)
from packages.core.utils.db import get_db

router = APIRouter()


@router.get("", response_model=list[Actor])
async def list_actors(
    actor_type: Optional[ActorType] = None,
    nationality: Optional[str] = None,
    organization: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """
    List actors with optional filtering.

    - **actor_type**: Filter by type (perpetrator, victim, entity, witness, official)
    - **nationality**: Filter by nationality
    - **organization**: Filter by organization
    - **search**: Full-text search in names
    """
    db = await get_db()

    query = "SELECT * FROM actors WHERE 1=1"
    params = []
    param_idx = 1

    if actor_type:
        query += f" AND actor_type = ${param_idx}"
        params.append(actor_type.value)
        param_idx += 1

    if nationality:
        query += f" AND nationality ILIKE ${param_idx}"
        params.append(f"%{nationality}%")
        param_idx += 1

    if organization:
        query += f" AND organization ILIKE ${param_idx}"
        params.append(f"%{organization}%")
        param_idx += 1

    if search:
        query += f" AND (name ILIKE ${param_idx} OR name_korean ILIKE ${param_idx} OR name_russian ILIKE ${param_idx})"
        params.append(f"%{search}%")
        param_idx += 1

    query += f" ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
    params.extend([limit, offset])

    rows = await db.fetch(query, *params)
    return [dict(row) for row in rows]


@router.post("", response_model=Actor)
async def create_actor(actor: ActorCreate):
    """Create a new actor."""
    db = await get_db()

    row = await db.fetchrow(
        """
        INSERT INTO actors (name, name_korean, name_russian, actor_type, nationality,
                           organization, position, date_of_birth, aliases, description,
                           photo_url, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        RETURNING *
        """,
        actor.name,
        actor.name_korean,
        actor.name_russian,
        actor.actor_type.value,
        actor.nationality,
        actor.organization,
        actor.position,
        actor.date_of_birth,
        actor.aliases,
        actor.description,
        actor.photo_url,
        actor.metadata,
    )

    return dict(row)


@router.get("/{actor_id}", response_model=Actor)
async def get_actor(actor_id: UUID):
    """Get a specific actor by ID."""
    db = await get_db()

    row = await db.fetchrow("SELECT * FROM actors WHERE id = $1", actor_id)

    if not row:
        raise HTTPException(status_code=404, detail="Actor not found")

    return dict(row)


@router.patch("/{actor_id}", response_model=Actor)
async def update_actor(actor_id: UUID, update: ActorUpdate):
    """Update an existing actor."""
    db = await get_db()

    # Build dynamic update query
    updates = []
    params = []
    param_idx = 1

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "actor_type" and value:
            value = value.value
        updates.append(f"{field} = ${param_idx}")
        params.append(value)
        param_idx += 1

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    params.append(actor_id)
    query = f"UPDATE actors SET {', '.join(updates)} WHERE id = ${param_idx} RETURNING *"

    row = await db.fetchrow(query, *params)

    if not row:
        raise HTTPException(status_code=404, detail="Actor not found")

    return dict(row)


@router.delete("/{actor_id}")
async def delete_actor(actor_id: UUID):
    """Delete an actor."""
    db = await get_db()

    result = await db.execute("DELETE FROM actors WHERE id = $1", actor_id)

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Actor not found")

    return {"status": "deleted", "id": str(actor_id)}


@router.get("/{actor_id}/chain", response_model=dict)
async def get_chain_of_command(
    actor_id: UUID,
    direction: str = Query(default="both", regex="^(up|down|both)$"),
    depth: int = Query(default=3, ge=1, le=10),
):
    """
    Get the chain of command for an actor.

    - **direction**: 'up' for superiors, 'down' for subordinates, 'both' for full chain
    - **depth**: Maximum depth to traverse (1-10)
    """
    db = await get_db()

    # Verify actor exists
    actor = await db.fetchrow("SELECT * FROM actors WHERE id = $1", actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")

    result = {
        "actor": dict(actor),
        "superiors": [],
        "subordinates": [],
    }

    if direction in ("up", "both"):
        # Get superiors recursively
        superiors = await _get_chain_recursive(db, actor_id, "up", depth)
        result["superiors"] = superiors

    if direction in ("down", "both"):
        # Get subordinates recursively
        subordinates = await _get_chain_recursive(db, actor_id, "down", depth)
        result["subordinates"] = subordinates

    return result


async def _get_chain_recursive(db, actor_id: UUID, direction: str, max_depth: int, current_depth: int = 0):
    """Recursively get chain of command."""
    if current_depth >= max_depth:
        return []

    if direction == "up":
        query = """
            SELECT c.*, a.*
            FROM chain_of_command c
            JOIN actors a ON c.superior_id = a.id
            WHERE c.subordinate_id = $1
        """
    else:
        query = """
            SELECT c.*, a.*
            FROM chain_of_command c
            JOIN actors a ON c.subordinate_id = a.id
            WHERE c.superior_id = $1
        """

    rows = await db.fetch(query, actor_id)

    results = []
    for row in rows:
        row_dict = dict(row)
        next_id = row_dict["superior_id"] if direction == "up" else row_dict["subordinate_id"]

        # Recursively get next level
        children = await _get_chain_recursive(db, next_id, direction, max_depth, current_depth + 1)

        results.append({
            "relationship": {
                "type": row_dict["relationship_type"],
                "organization": row_dict["organization"],
                "confidence_score": row_dict["confidence_score"],
            },
            "actor": {
                "id": str(row_dict["id"]),
                "name": row_dict["name"],
                "position": row_dict["position"],
                "organization": row_dict["organization"],
            },
            "children": children if direction == "down" else [],
            "parents": children if direction == "up" else [],
        })

    return results


@router.post("/{actor_id}/chain", response_model=ChainOfCommand)
async def create_chain_relationship(actor_id: UUID, relationship: ChainOfCommandCreate):
    """Create a chain of command relationship."""
    db = await get_db()

    # Verify both actors exist
    superior = await db.fetchrow("SELECT id FROM actors WHERE id = $1", relationship.superior_id)
    subordinate = await db.fetchrow("SELECT id FROM actors WHERE id = $1", relationship.subordinate_id)

    if not superior:
        raise HTTPException(status_code=404, detail="Superior actor not found")
    if not subordinate:
        raise HTTPException(status_code=404, detail="Subordinate actor not found")

    row = await db.fetchrow(
        """
        INSERT INTO chain_of_command (superior_id, subordinate_id, relationship_type,
                                     organization, start_date, end_date, evidence_ids,
                                     confidence_score, notes, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING *
        """,
        relationship.superior_id,
        relationship.subordinate_id,
        relationship.relationship_type,
        relationship.organization,
        relationship.start_date,
        relationship.end_date,
        relationship.evidence_ids,
        relationship.confidence_score,
        relationship.notes,
        relationship.metadata,
    )

    return dict(row)
