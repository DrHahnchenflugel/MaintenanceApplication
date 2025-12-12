from sqlalchemy import text
from app.db.connection import get_connection

def list_site_rows():
    sql = text("""
        SELECT
            id,
            shorthand,
            fullname
        FROM site
        ORDER BY fullname ASC, shorthand ASC
    """)

    with get_connection() as conn:
        rows = conn.execute(sql).mappings().all()

    return [dict(r) for r in rows]

def get_site_row(site_id):
    sql = text("""
        SELECT
            id,
            shorthand,
            fullname
        FROM site
        WHERE id = :id
    """)

    with get_connection() as conn:
        row = conn.execute(sql, {"id": site_id}).mappings().first()

    if row is None:
        return None

    return dict(row)
