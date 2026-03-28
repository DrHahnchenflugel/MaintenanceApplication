from sqlalchemy import text

from app.db.connection import get_connection


def get_admin_gate_row(name: str):
    sql = text("""
        SELECT
            id,
            name,
            password_hash,
            is_enabled
        FROM admin_gate
        WHERE name = :name
    """)

    with get_connection() as conn:
        row = conn.execute(sql, {"name": name}).mappings().first()

    if row is None:
        return None

    return dict(row)


def admin_gate_exists(name: str) -> bool:
    sql = text("""
        SELECT 1
        FROM admin_gate
        WHERE name = :name
    """)

    with get_connection() as conn:
        row = conn.execute(sql, {"name": name}).mappings().first()

    return row is not None


def is_admin_gate_enabled(name: str) -> bool:
    sql = text("""
        SELECT is_enabled
        FROM admin_gate
        WHERE name = :name
    """)

    with get_connection() as conn:
        row = conn.execute(sql, {"name": name}).mappings().first()

    if row is None:
        return False

    return bool(row["is_enabled"])
