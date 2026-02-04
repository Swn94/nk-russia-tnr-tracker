"""Database connection and session management."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg
from asyncpg import Pool

from .config import get_settings


class Database:
    """Async PostgreSQL database connection manager."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or get_settings().database_url
        self._pool: Optional[Pool] = None

    async def connect(self) -> None:
        """Create connection pool."""
        if self._pool is None:
            settings = get_settings()
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=settings.db_pool_size + settings.db_max_overflow,
            )

    async def disconnect(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    @property
    def pool(self) -> Pool:
        """Get the connection pool."""
        if self._pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._pool

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get a database connection from the pool."""
        async with self.pool.acquire() as conn:
            yield conn

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get a database connection with transaction."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn

    async def execute(self, query: str, *args) -> str:
        """Execute a query and return status."""
        async with self.connection() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args) -> list[asyncpg.Record]:
        """Fetch all rows from a query."""
        async with self.connection() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Fetch a single row from a query."""
        async with self.connection() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        """Fetch a single value from a query."""
        async with self.connection() as conn:
            return await conn.fetchval(query, *args)


# Global database instance
_db: Optional[Database] = None


async def get_db() -> Database:
    """Get the global database instance."""
    global _db
    if _db is None:
        _db = Database()
        await _db.connect()
    return _db


async def close_db() -> None:
    """Close the global database connection."""
    global _db
    if _db:
        await _db.disconnect()
        _db = None
