"""AI-powered analysis module using installed tools (CrewAI, Anthropic)."""

from typing import Any, Optional

import structlog

logger = structlog.get_logger()


class TNRAnalyzer:
    """AI analysis for TNR cases using CrewAI multi-agent framework."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    async def analyze_case(self, case_data: dict[str, Any]) -> dict[str, Any]:
        """Analyze a TNR case using AI to identify patterns and connections."""
        try:
            from crewai import Agent, Task, Crew

            researcher = Agent(
                role="Human Rights Researcher",
                goal="Analyze TNR case data for patterns of transnational repression",
                backstory="Expert in North Korea-Russia human rights documentation",
                verbose=False,
            )

            analyst = Agent(
                role="Sanctions Analyst",
                goal="Identify sanctions candidates from case evidence",
                backstory="Expert in international sanctions frameworks (EU, US, UN)",
                verbose=False,
            )

            research_task = Task(
                description=f"Analyze this TNR case and identify key actors, violations, and evidence chain: {case_data.get('summary', '')}",
                agent=researcher,
                expected_output="Structured analysis with actors, violations, and evidence assessment",
            )

            sanctions_task = Task(
                description="Based on the research, identify potential sanctions candidates with justification",
                agent=analyst,
                expected_output="List of sanctions candidates with designation criteria",
            )

            crew = Crew(
                agents=[researcher, analyst],
                tasks=[research_task, sanctions_task],
                verbose=False,
            )

            result = crew.kickoff()

            return {
                "status": "success",
                "analysis": str(result),
                "method": "crewai_multi_agent",
            }

        except ImportError:
            logger.warning("CrewAI not available, falling back to basic analysis")
            return await self._basic_analysis(case_data)
        except Exception as e:
            logger.error("AI analysis failed", error=str(e))
            return {"status": "error", "error": str(e)}

    async def _basic_analysis(self, case_data: dict[str, Any]) -> dict[str, Any]:
        """Fallback basic analysis without AI framework."""
        return {
            "status": "success",
            "analysis": f"Basic analysis of case: {case_data.get('title', 'Unknown')}",
            "method": "basic",
            "tnr_type": case_data.get("tnr_type"),
            "actors_count": len(case_data.get("actors", [])),
        }

    async def generate_briefing(
        self,
        cases: list[dict[str, Any]],
        format: str = "markdown",
    ) -> str:
        """Generate a comprehensive briefing document from cases."""
        from datetime import datetime

        header = f"# NK-Russia TNR Briefing\n\nGenerated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        sections = []

        for case in cases:
            section = f"## {case.get('title', 'Untitled')}\n\n"
            section += f"- **TNR Type**: {case.get('tnr_type', 'Unknown')}\n"
            section += f"- **Country**: {case.get('country', 'Unknown')}\n"
            section += f"- **Status**: {case.get('status', 'Unknown')}\n"
            if case.get("summary"):
                section += f"\n{case['summary']}\n"
            sections.append(section)

        return header + "\n---\n\n".join(sections)
