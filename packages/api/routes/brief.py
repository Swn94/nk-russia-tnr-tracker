"""Briefing generation API endpoints."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from packages.core.utils.db import get_db

router = APIRouter()


class BriefRequest(BaseModel):
    """Request model for generating a briefing."""
    title: str = Field(..., description="Title of the briefing")
    actor_ids: list[UUID] = Field(default_factory=list, description="Actor IDs to include")
    case_ids: list[UUID] = Field(default_factory=list, description="Case IDs to include")
    candidate_ids: list[UUID] = Field(default_factory=list, description="Sanctions candidate IDs to include")
    include_chain_of_command: bool = Field(default=True, description="Include chain of command analysis")
    include_evidence_summary: bool = Field(default=True, description="Include evidence summary")
    date_from: Optional[date] = Field(default=None, description="Start date for case filtering")
    date_to: Optional[date] = Field(default=None, description="End date for case filtering")
    format: str = Field(default="markdown", description="Output format (markdown, html, json)")


class BriefResponse(BaseModel):
    """Response model for generated briefing."""
    title: str
    generated_at: datetime
    content: str
    format: str
    metadata: dict


@router.post("/generate", response_model=BriefResponse)
async def generate_brief(request: BriefRequest):
    """
    Generate a comprehensive briefing document.

    The briefing includes:
    - Executive summary
    - Actor profiles
    - Case summaries
    - Chain of command analysis
    - Evidence summary
    - Sanctions recommendations
    """
    db = await get_db()

    sections = []

    # Header
    sections.append(f"# {request.title}")
    sections.append(f"\n**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n")

    # Executive Summary
    sections.append("## Executive Summary\n")

    actor_count = len(request.actor_ids)
    case_count = len(request.case_ids)
    candidate_count = len(request.candidate_ids)

    sections.append(f"This briefing covers **{actor_count}** actors, **{case_count}** cases, and **{candidate_count}** sanctions candidates.\n")

    # Actors Section
    if request.actor_ids:
        sections.append("## Actors\n")

        for actor_id in request.actor_ids:
            actor = await db.fetchrow("SELECT * FROM actors WHERE id = $1", actor_id)
            if actor:
                sections.append(f"### {actor['name']}")
                if actor['name_korean']:
                    sections.append(f"({actor['name_korean']})")
                sections.append("")

                if actor['position']:
                    sections.append(f"- **Position:** {actor['position']}")
                if actor['organization']:
                    sections.append(f"- **Organization:** {actor['organization']}")
                if actor['nationality']:
                    sections.append(f"- **Nationality:** {actor['nationality']}")
                if actor['description']:
                    sections.append(f"\n{actor['description']}\n")

                # Chain of command if requested
                if request.include_chain_of_command:
                    chain = await db.fetch(
                        """
                        SELECT c.*, a.name as related_name, a.position as related_position
                        FROM chain_of_command c
                        JOIN actors a ON c.superior_id = a.id
                        WHERE c.subordinate_id = $1
                        """,
                        actor_id,
                    )
                    if chain:
                        sections.append("\n**Reports to:**")
                        for c in chain:
                            sections.append(f"- {c['related_name']} ({c['related_position'] or 'Unknown position'})")

                sections.append("")

    # Cases Section
    if request.case_ids:
        sections.append("## Cases\n")

        for case_id in request.case_ids:
            case = await db.fetchrow("SELECT * FROM cases WHERE id = $1", case_id)
            if case:
                sections.append(f"### {case['title']}")
                if case['case_number']:
                    sections.append(f"Case Number: {case['case_number']}")
                sections.append("")

                if case['date_occurred']:
                    sections.append(f"- **Date:** {case['date_occurred']}")
                if case['location']:
                    sections.append(f"- **Location:** {case['location']}, {case['country'] or ''}")
                if case['tnr_type']:
                    sections.append(f"- **TNR Type:** {case['tnr_type']}")
                if case['severity_score']:
                    sections.append(f"- **Severity:** {case['severity_score']}/10")
                if case['status']:
                    sections.append(f"- **Status:** {case['status']}")

                if case['summary']:
                    sections.append(f"\n{case['summary']}\n")

                # Evidence summary if requested
                if request.include_evidence_summary:
                    evidence = await db.fetch(
                        "SELECT evidence_type, COUNT(*) as count FROM evidence WHERE case_id = $1 GROUP BY evidence_type",
                        case_id,
                    )
                    if evidence:
                        sections.append("\n**Evidence:**")
                        for e in evidence:
                            sections.append(f"- {e['evidence_type']}: {e['count']} item(s)")

                sections.append("")

    # Sanctions Candidates Section
    if request.candidate_ids:
        sections.append("## Sanctions Candidates\n")

        for candidate_id in request.candidate_ids:
            candidate = await db.fetchrow(
                """
                SELECT sc.*, a.name as actor_name, a.position, a.organization
                FROM sanctions_candidates sc
                JOIN actors a ON sc.actor_id = a.id
                WHERE sc.id = $1
                """,
                candidate_id,
            )
            if candidate:
                sections.append(f"### {candidate['actor_name']}")
                sections.append("")

                sections.append(f"- **Status:** {candidate['status']}")
                if candidate['priority_level']:
                    sections.append(f"- **Priority Level:** {candidate['priority_level']}")
                if candidate['evidence_strength_score']:
                    sections.append(f"- **Evidence Strength:** {candidate['evidence_strength_score']:.2f}")
                if candidate['legal_basis']:
                    sections.append(f"- **Legal Basis:** {candidate['legal_basis']}")

                if candidate['proposed_sanctions']:
                    sections.append("\n**Proposed Sanctions:**")
                    for sanction in candidate['proposed_sanctions']:
                        sections.append(f"- {sanction}")

                sections.append("")

    # Footer
    sections.append("---")
    sections.append(f"\n*This briefing was auto-generated by the NK-Russia TNR Tracker system.*")

    content = "\n".join(sections)

    # Convert to HTML if requested
    if request.format == "html":
        try:
            import markdown
            content = markdown.markdown(content, extensions=['tables', 'fenced_code'])
            content = f"<!DOCTYPE html><html><head><title>{request.title}</title></head><body>{content}</body></html>"
        except ImportError:
            pass  # Return markdown if markdown library not available

    return BriefResponse(
        title=request.title,
        generated_at=datetime.utcnow(),
        content=content,
        format=request.format,
        metadata={
            "actor_count": len(request.actor_ids),
            "case_count": len(request.case_ids),
            "candidate_count": len(request.candidate_ids),
        },
    )


@router.get("/templates")
async def list_templates():
    """List available briefing templates."""
    return [
        {
            "id": "executive_summary",
            "name": "Executive Summary",
            "description": "High-level overview for leadership",
        },
        {
            "id": "case_detail",
            "name": "Case Detail Report",
            "description": "Detailed analysis of specific cases",
        },
        {
            "id": "chain_of_command",
            "name": "Chain of Command Analysis",
            "description": "Hierarchical responsibility mapping",
        },
        {
            "id": "sanctions_recommendation",
            "name": "Sanctions Recommendation",
            "description": "Formal recommendation for sanctions action",
        },
    ]


@router.get("/recent")
async def get_recent_activity(
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Get recent activity for quick briefing."""
    db = await get_db()

    # Recent cases
    recent_cases = await db.fetch(
        """
        SELECT id, title, tnr_type, severity_score, created_at
        FROM cases
        WHERE created_at > CURRENT_DATE - $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        days,
        limit,
    )

    # Recent sanctions updates
    recent_sanctions = await db.fetch(
        """
        SELECT sc.id, sc.status, sc.updated_at, a.name as actor_name
        FROM sanctions_candidates sc
        JOIN actors a ON sc.actor_id = a.id
        WHERE sc.updated_at > CURRENT_DATE - $1
        ORDER BY sc.updated_at DESC
        LIMIT $2
        """,
        days,
        limit,
    )

    return {
        "period_days": days,
        "recent_cases": [dict(row) for row in recent_cases],
        "recent_sanctions_updates": [dict(row) for row in recent_sanctions],
    }
