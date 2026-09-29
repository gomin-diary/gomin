from collections.abc import AsyncIterator

from fastapi import Request
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool


def create_pool(database_url: str) -> AsyncConnectionPool:
    return AsyncConnectionPool(
        conninfo=database_url,
        open=False,
        min_size=1,
        max_size=5,
        timeout=5,
        kwargs={"connect_timeout": 5, "options": "-c statement_timeout=5000"},
        check=AsyncConnectionPool.check_connection,
    )


async def get_connection(request: Request) -> AsyncIterator[AsyncConnection]:
    async with request.app.state.db_pool.connection() as connection:
        yield connection
