"""ETL Pipeline orchestration for NK-Russia TNR Tracker."""

import asyncio
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

import structlog

from packages.core.utils.config import get_settings
from packages.core.utils.db import get_db, close_db
from packages.etl.connectors import (
    DataGoKrConnector,
    HUDOCConnector,
    FreedomHouseConnector,
    UNOHCHRConnector,
    ICCConnector,
    OSCEConnector,
    TJWGFootprintsConnector,
)
from packages.etl.processors import MarkerConverter, DocumentChunker

logger = structlog.get_logger()


class ETLPipeline:
    """Main ETL pipeline orchestrator."""

    def __init__(self):
        self.settings = get_settings()
        self.connectors = {
            "data.go.kr": DataGoKrConnector,
            "hudoc": HUDOCConnector,
            "freedom_house": FreedomHouseConnector,
            "un_ohchr": UNOHCHRConnector,
            "icc": ICCConnector,
            "osce": OSCEConnector,
            "tjwg_footprints": TJWGFootprintsConnector,
        }
        self.pdf_converter = MarkerConverter()
        self.chunker = DocumentChunker()

    async def run_connector(
        self,
        connector_name: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Run a specific data connector."""
        if connector_name not in self.connectors:
            return {
                "status": "error",
                "error": f"Unknown connector: {connector_name}",
            }

        connector_class = self.connectors[connector_name]
        async with connector_class() as connector:
            result = await connector.sync(**kwargs)

        return result

    async def run_all_connectors(
        self,
        connectors: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Run all or specified connectors."""
        target_connectors = connectors or list(self.connectors.keys())
        results = {}
        errors = []

        for name in target_connectors:
            try:
                logger.info("Running connector", connector=name)
                result = await self.run_connector(name)
                results[name] = result

                if result.get("status") == "error":
                    errors.append({
                        "connector": name,
                        "error": result.get("error"),
                    })

            except Exception as e:
                logger.error("Connector failed", connector=name, error=str(e))
                errors.append({
                    "connector": name,
                    "error": str(e),
                })
                results[name] = {
                    "status": "error",
                    "error": str(e),
                }

        return {
            "status": "completed" if not errors else "completed_with_errors",
            "connectors_run": len(target_connectors),
            "successful": len(target_connectors) - len(errors),
            "errors": errors,
            "results": results,
        }

    async def process_pdf(
        self,
        pdf_path: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Process a PDF file: convert to markdown and chunk."""
        # Convert PDF
        conversion_result = await self.pdf_converter.convert_pdf(pdf_path, **kwargs)

        if conversion_result.get("status") == "error":
            return conversion_result

        # Chunk the content
        content = conversion_result.get("content", "")
        chunks = self.chunker.chunk_markdown(
            content,
            source_id=pdf_path,
            metadata={
                "file_hash": conversion_result.get("file_hash"),
                "conversion_method": conversion_result.get("method"),
            },
        )

        return {
            "status": "success",
            "source_file": pdf_path,
            "output_file": conversion_result.get("output_file"),
            "file_hash": conversion_result.get("file_hash"),
            "conversion_method": conversion_result.get("method"),
            "char_count": conversion_result.get("char_count"),
            "chunk_count": len(chunks),
            "chunks": self.chunker.to_dict_list(chunks),
        }

    async def save_to_database(
        self,
        data: list[dict],
        table: str,
    ) -> dict[str, Any]:
        """Save transformed data to database."""
        db = await get_db()
        created = 0
        updated = 0
        errors = []

        for item in data:
            try:
                # Determine insert or update based on unique keys
                if table == "cases":
                    await self._upsert_case(db, item)
                    created += 1
                elif table == "actors":
                    await self._upsert_actor(db, item)
                    created += 1
                elif table == "evidence":
                    await self._insert_evidence(db, item)
                    created += 1
                elif table == "defector_stats":
                    result = await self._upsert_defector_stats(db, item)
                    if result == "created":
                        created += 1
                    else:
                        updated += 1
                elif table == "footprints_victims":
                    result = await self._upsert_footprints_victim(db, item)
                    if result == "created":
                        created += 1
                    else:
                        updated += 1
                elif table == "footprints_perpetrators":
                    result = await self._upsert_footprints_perpetrator(db, item)
                    if result == "created":
                        created += 1
                    else:
                        updated += 1
                elif table == "footprints_proceedings":
                    result = await self._upsert_footprints_proceeding(db, item)
                    if result == "created":
                        created += 1
                    else:
                        updated += 1

            except Exception as e:
                errors.append({
                    "item": item.get("title") or item.get("name") or item.get("year"),
                    "error": str(e),
                })

        return {
            "status": "completed" if not errors else "completed_with_errors",
            "table": table,
            "created": created,
            "updated": updated,
            "errors": errors,
        }

    async def _upsert_case(self, db, data: dict) -> None:
        """Insert or update a case."""
        await db.execute(
            """
            INSERT INTO cases (title, title_korean, case_number, status, tnr_type,
                              date_occurred, country, summary, source_urls, tags, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (case_number) DO UPDATE SET
                title = EXCLUDED.title,
                summary = EXCLUDED.summary,
                source_urls = EXCLUDED.source_urls,
                metadata = EXCLUDED.metadata,
                updated_at = CURRENT_TIMESTAMP
            """,
            data.get("title"),
            data.get("title_korean"),
            data.get("case_number"),
            data.get("status", "open"),
            data.get("tnr_type"),
            data.get("date_occurred"),
            data.get("country"),
            data.get("summary"),
            data.get("source_urls", []),
            data.get("tags", []),
            data.get("metadata", {}),
        )

    async def _upsert_actor(self, db, data: dict) -> None:
        """Insert or update an actor."""
        await db.execute(
            """
            INSERT INTO actors (name, name_korean, name_russian, actor_type,
                               nationality, organization, position, aliases,
                               description, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            data.get("name"),
            data.get("name_korean"),
            data.get("name_russian"),
            data.get("actor_type"),
            data.get("nationality"),
            data.get("organization"),
            data.get("position"),
            data.get("aliases", []),
            data.get("description"),
            data.get("metadata", {}),
        )

    async def _insert_evidence(self, db, data: dict) -> None:
        """Insert evidence."""
        await db.execute(
            """
            INSERT INTO evidence (case_id, evidence_type, title, description,
                                 source_name, source_url, raw_content, processed_content,
                                 metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            data.get("case_id"),
            data.get("evidence_type"),
            data.get("title"),
            data.get("description"),
            data.get("source_name"),
            data.get("source_url"),
            data.get("raw_content"),
            data.get("processed_content"),
            data.get("metadata", {}),
        )

    async def _upsert_defector_stats(self, db, data: dict) -> str:
        """Insert or update defector statistics from data.go.kr."""
        import json
        category = data.get("category", "")
        raw_json = json.dumps(data.get("raw_data", {}))

        if "yearly" in category:
            result = await db.execute(
                """
                INSERT INTO defector_stats_yearly (year, total, male, female, raw_data)
                VALUES ($1, $2, $3, $4, $5::jsonb)
                ON CONFLICT (year) DO UPDATE SET
                    total = EXCLUDED.total,
                    male = EXCLUDED.male,
                    female = EXCLUDED.female,
                    raw_data = EXCLUDED.raw_data,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING (xmax = 0) AS is_insert
                """,
                int(data.get("year") or 0),
                int(data.get("total") or 0),
                int(data.get("male") or 0),
                int(data.get("female") or 0),
                raw_json,
            )
        elif "age" in category:
            from datetime import date
            result = await db.execute(
                """
                INSERT INTO defector_stats_age (age_group, count, as_of_date, raw_data)
                VALUES ($1, $2, $3, $4::jsonb)
                ON CONFLICT (age_group, as_of_date) DO UPDATE SET
                    count = EXCLUDED.count,
                    raw_data = EXCLUDED.raw_data,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING (xmax = 0) AS is_insert
                """,
                data.get("age_group"),
                int(data.get("count") or 0),
                date.today(),
                raw_json,
            )
        elif "occupation" in category:
            from datetime import date
            result = await db.execute(
                """
                INSERT INTO defector_stats_occupation (occupation, count, as_of_date, raw_data)
                VALUES ($1, $2, $3, $4::jsonb)
                ON CONFLICT (occupation, as_of_date) DO UPDATE SET
                    count = EXCLUDED.count,
                    raw_data = EXCLUDED.raw_data,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING (xmax = 0) AS is_insert
                """,
                data.get("occupation"),
                int(data.get("count") or 0),
                date.today(),
                raw_json,
            )
        elif "region" in category:
            from datetime import date
            result = await db.execute(
                """
                INSERT INTO defector_stats_region (region, count, as_of_date, raw_data)
                VALUES ($1, $2, $3, $4::jsonb)
                ON CONFLICT (region, as_of_date) DO UPDATE SET
                    count = EXCLUDED.count,
                    raw_data = EXCLUDED.raw_data,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING (xmax = 0) AS is_insert
                """,
                data.get("region"),
                int(data.get("count") or 0),
                date.today(),
                raw_json,
            )
        else:
            return "skipped"

        return "created"

    async def _upsert_footprints_victim(self, db, data: dict) -> str:
        """Insert or update FOOTPRINTS victim record."""
        import json
        result = await db.execute(
            """
            INSERT INTO footprints_victims (
                external_id, name, name_korean, victim_type, gender,
                age_at_incident, nationality, occupation, date_of_incident,
                place_of_incident, last_known_location, current_status,
                related_perpetrator_ids, related_proceeding_ids,
                source_url, source_urls, metadata, language, fetch_date
            )
            VALUES ($1, $2, $3, $4::footprints_victim_type, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17::jsonb, $18, $19)
            ON CONFLICT (external_id) DO UPDATE SET
                name = EXCLUDED.name,
                name_korean = EXCLUDED.name_korean,
                current_status = EXCLUDED.current_status,
                related_perpetrator_ids = EXCLUDED.related_perpetrator_ids,
                related_proceeding_ids = EXCLUDED.related_proceeding_ids,
                metadata = EXCLUDED.metadata,
                fetch_date = EXCLUDED.fetch_date,
                updated_at = CURRENT_TIMESTAMP
            RETURNING (xmax = 0) AS is_insert
            """,
            data.get("external_id"),
            data.get("name"),
            data.get("name_korean"),
            data.get("victim_type", "other"),
            data.get("gender"),
            data.get("age_at_incident"),
            data.get("nationality"),
            data.get("occupation"),
            data.get("date_of_incident"),
            data.get("place_of_incident"),
            data.get("last_known_location"),
            data.get("status"),
            data.get("related_perpetrators", []),
            data.get("related_proceedings", []),
            data.get("source_url"),
            data.get("source_urls", []),
            json.dumps(data.get("metadata", {})),
            data.get("language", "en"),
            data.get("fetch_date"),
        )
        return "created"

    async def _upsert_footprints_perpetrator(self, db, data: dict) -> str:
        """Insert or update FOOTPRINTS perpetrator record."""
        import json
        result = await db.execute(
            """
            INSERT INTO footprints_perpetrators (
                external_id, name, name_korean, perpetrator_type,
                organization_name, position, period_description,
                related_victim_ids, related_case_ids,
                source_url, source_urls, metadata, language, fetch_date
            )
            VALUES ($1, $2, $3, $4::footprints_perpetrator_type, $5, $6, $7, $8, $9, $10, $11, $12::jsonb, $13, $14)
            ON CONFLICT (external_id) DO UPDATE SET
                name = EXCLUDED.name,
                name_korean = EXCLUDED.name_korean,
                position = EXCLUDED.position,
                related_victim_ids = EXCLUDED.related_victim_ids,
                metadata = EXCLUDED.metadata,
                fetch_date = EXCLUDED.fetch_date,
                updated_at = CURRENT_TIMESTAMP
            RETURNING (xmax = 0) AS is_insert
            """,
            data.get("external_id"),
            data.get("name"),
            data.get("name_korean"),
            data.get("perpetrator_type", "other"),
            data.get("organization"),
            data.get("position"),
            data.get("period_active"),
            data.get("related_victims", []),
            data.get("related_cases", []),
            data.get("source_url"),
            data.get("source_urls", []),
            json.dumps(data.get("metadata", {})),
            data.get("language", "en"),
            data.get("fetch_date"),
        )
        return "created"

    async def _upsert_footprints_proceeding(self, db, data: dict) -> str:
        """Insert or update FOOTPRINTS proceeding record."""
        import json
        result = await db.execute(
            """
            INSERT INTO footprints_proceedings (
                external_id, title, title_korean, proceeding_type, forum_name,
                date_initiated, status, outcome, description,
                related_victim_ids, related_perpetrator_ids,
                document_urls, source_url, source_urls, metadata, language, fetch_date
            )
            VALUES ($1, $2, $3, $4::footprints_proceeding_type, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15::jsonb, $16, $17)
            ON CONFLICT (external_id) DO UPDATE SET
                title = EXCLUDED.title,
                status = EXCLUDED.status,
                outcome = EXCLUDED.outcome,
                related_victim_ids = EXCLUDED.related_victim_ids,
                related_perpetrator_ids = EXCLUDED.related_perpetrator_ids,
                document_urls = EXCLUDED.document_urls,
                metadata = EXCLUDED.metadata,
                fetch_date = EXCLUDED.fetch_date,
                updated_at = CURRENT_TIMESTAMP
            RETURNING (xmax = 0) AS is_insert
            """,
            data.get("external_id"),
            data.get("proceeding_title") or data.get("title"),
            data.get("title_korean"),
            data.get("proceeding_type", "other"),
            data.get("forum"),
            data.get("date_initiated"),
            data.get("status"),
            data.get("outcome"),
            data.get("description"),
            data.get("related_victims", []),
            data.get("related_perpetrators", []),
            [d.get("url") for d in data.get("documents", []) if d.get("url")],
            data.get("source_url"),
            data.get("source_urls", []),
            json.dumps(data.get("metadata", {})),
            data.get("language", "en"),
            data.get("fetch_date"),
        )
        return "created"

    async def log_etl_job(
        self,
        source_name: str,
        job_type: str,
        status: str,
        records_processed: int = 0,
        records_created: int = 0,
        records_updated: int = 0,
        error_message: Optional[str] = None,
    ) -> None:
        """Log ETL job to database."""
        db = await get_db()

        # Get source ID
        source_row = await db.fetchrow(
            "SELECT id FROM data_sources WHERE name = $1",
            source_name,
        )

        await db.execute(
            """
            INSERT INTO etl_logs (source_id, job_type, status, records_processed,
                                 records_created, records_updated, error_message,
                                 completed_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, CURRENT_TIMESTAMP)
            """,
            source_row["id"] if source_row else None,
            job_type,
            status,
            records_processed,
            records_created,
            records_updated,
            error_message,
        )

    async def run_nightly_etl(self) -> dict[str, Any]:
        """Run the nightly ETL job."""
        start_time = datetime.utcnow()
        logger.info("Starting nightly ETL job")

        results = {
            "start_time": start_time.isoformat(),
            "connectors": {},
            "total_records": 0,
            "errors": [],
        }

        try:
            # Run all connectors
            connector_results = await self.run_all_connectors()
            results["connectors"] = connector_results

            # Calculate totals
            for name, result in connector_results.get("results", {}).items():
                if result.get("status") == "success":
                    results["total_records"] += result.get("records_transformed", 0)

                    # Log successful job
                    await self.log_etl_job(
                        source_name=name,
                        job_type="nightly_sync",
                        status="success",
                        records_processed=result.get("records_fetched", 0),
                        records_created=result.get("records_transformed", 0),
                    )
                else:
                    results["errors"].append({
                        "connector": name,
                        "error": result.get("error"),
                    })

                    # Log failed job
                    await self.log_etl_job(
                        source_name=name,
                        job_type="nightly_sync",
                        status="error",
                        error_message=result.get("error"),
                    )

        except Exception as e:
            logger.error("Nightly ETL failed", error=str(e))
            results["errors"].append({"error": str(e)})

        finally:
            end_time = datetime.utcnow()
            results["end_time"] = end_time.isoformat()
            results["duration_seconds"] = (end_time - start_time).total_seconds()

        logger.info(
            "Nightly ETL completed",
            total_records=results["total_records"],
            errors=len(results["errors"]),
            duration=results["duration_seconds"],
        )

        return results


async def main():
    """CLI entry point for ETL pipeline."""
    import argparse

    parser = argparse.ArgumentParser(description="NK-Russia TNR Tracker ETL Pipeline")
    parser.add_argument(
        "--connector",
        choices=["all", "data.go.kr", "hudoc", "freedom_house", "un_ohchr", "icc", "osce", "tjwg_footprints"],
        default="all",
        help="Connector to run",
    )
    parser.add_argument(
        "--pdf",
        help="PDF file to process",
    )
    parser.add_argument(
        "--nightly",
        action="store_true",
        help="Run nightly ETL job",
    )

    args = parser.parse_args()

    pipeline = ETLPipeline()

    try:
        if args.nightly:
            result = await pipeline.run_nightly_etl()
        elif args.pdf:
            result = await pipeline.process_pdf(args.pdf)
        elif args.connector == "all":
            result = await pipeline.run_all_connectors()
        else:
            result = await pipeline.run_connector(args.connector)

        print(result)

    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
