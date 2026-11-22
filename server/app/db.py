from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from .config import settings

# autocommit: each statement saves at once. Use `async with conn.transaction():`
# when several statements must succeed together.
pool = AsyncConnectionPool(
    settings.database_url,
    open=False,
    min_size=1,
    max_size=5,
    kwargs={"row_factory": dict_row, "autocommit": True, "prepare_threshold": None},
)