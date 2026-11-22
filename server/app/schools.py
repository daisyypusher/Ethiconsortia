from dataclasses import dataclass
from typing import Protocol

import psycopg
from psycopg.rows import dict_row

from .codes import hash_code
from .config import settings


class CodeRejected(Exception):
    """Unknown, used, expired, or not for the chosen account type.
    The reason is NOT shown to users on purpose."""


@dataclass
class StaffRecord:
    ref: str                       # employee number at the school
    full_name: str
    role: str                      # 'professor' | 'admin'
    department_id: str | None
    department_name: str | None


class SchoolVerifier(Protocol):
    async def redeem(self, code: str, role: str, consume: bool = True) -> StaffRecord: ...


_FIND_CODE = """
select c.code_id, s.employee_no, s.full_name, s.role,
       s.department_id, s.department_name
from staff_codes c
join staff s on s.staff_id = c.staff_id
where c.code_hash = %s
  and c.used_at is null
  and c.expires_at > now()
  and s.is_active
for update of c
"""


class DbSchoolVerifier:
    """Test school: talks straight to a separate Postgres. A real school would get
    an HttpSchoolVerifier with this same redeem() method."""

    def __init__(self, url: str):
        self.url = url

    async def redeem(self, code: str, role: str, consume: bool = True) -> StaffRecord:
        if not self.url:
            raise RuntimeError("DEMO_SCHOOL_DATABASE_URL is not set")
        conn = await psycopg.AsyncConnection.connect(
            self.url, row_factory=dict_row, autocommit=True, prepare_threshold=None)
        try:
            async with conn.transaction():
                cur = await conn.execute(_FIND_CODE, (hash_code(code),))
                row = await cur.fetchone()
                if not row or row["role"] != role:
                    raise CodeRejected()
                if consume:
                    await conn.execute(
                        "update staff_codes set used_at = now() where code_id = %s",
                        (row["code_id"],))
        finally:
            await conn.close()
        return StaffRecord(row["employee_no"], row["full_name"], row["role"],
                           row["department_id"], row["department_name"])


def get_verifier(adapter: str) -> SchoolVerifier:
    if adapter == "demo_db":
        return DbSchoolVerifier(settings.demo_school_database_url)
    raise ValueError(f"Unknown school adapter: {adapter}")