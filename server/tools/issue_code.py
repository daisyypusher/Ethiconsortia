import secrets
import sys

import psycopg

from app.codes import hash_code
from app.config import settings

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"   # no I, L, O, 0, 1


def make_code() -> str:
    raw = "".join(secrets.choice(ALPHABET) for _ in range(12))
    return f"{raw[:4]}-{raw[4:8]}-{raw[8:]}"


def main():
    if len(sys.argv) < 2:
        print("usage: python -m tools.issue_code EMPLOYEE_NO [days]")
        return
    emp = sys.argv[1]
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    with psycopg.connect(settings.demo_school_database_url,
                         autocommit=True, prepare_threshold=None) as conn:
        row = conn.execute(
            "select staff_id, full_name, role from staff "
            "where employee_no = %s and is_active", (emp,)).fetchone()
        if not row:
            print("No active staff with that employee number.")
            return
        code = make_code()
        conn.execute(
            "insert into staff_codes (staff_id, code_hash, expires_at) "
            "values (%s, %s, now() + make_interval(days => %s))",
            (row[0], hash_code(code), days))
    print(f"{row[1]} ({row[2]}): {code}   expires in {days} days")
    print("Shown once. Only a hash is stored.")


main()