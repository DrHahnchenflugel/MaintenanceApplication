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
