from sqlalchemy import text
from app.db.connection import get_connection

def list_asset_status_rows():
    sql = text("""
        SELECT
            id,
            code,
            label,
            display_order
        FROM asset_status
        ORDER BY display_order ASC, code ASC
    """)

    with get_connection() as conn:
        rows = conn.execute(sql).mappings().all()

    return [dict(r) for r in rows]

def list_asset_category_rows():
    sql = text("""
        SELECT
            id,
            code,
            label,
            display_order
        FROM asset_category
        ORDER BY display_order ASC, code ASC
    """)

    with get_connection() as conn:
        rows = conn.execute(sql).mappings().all()

    return [dict(r) for r in rows]
