from sqlalchemy import text
from app.db.connection import get_connection

def list_site_rows():
    sql = text("""
        SELECT
            id,
            code,
            name
        FROM site
        ORDER BY name ASC, code ASC
    """)

    with get_connection() as conn:
        rows = conn.execute(sql).mappings().all()

    return [dict(r) for r in rows]
