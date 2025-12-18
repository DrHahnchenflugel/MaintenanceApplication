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

def list_category_rows():
    sql = text("""
        SELECT
            id,
            name,
            label
        FROM category
        ORDER BY label ASC, name ASC
    """)

    with get_connection() as conn:
        rows = conn.execute(sql).mappings().all()

    return [dict(r) for r in rows]

def list_issue_status_rows():
    sql = text("""
        SELECT
            id,
            code,
            label,
            display_order
        FROM issue_status
        ORDER BY display_order ASC
    """)

    with get_connection() as conn:
        rows = conn.execute(sql).mappings().all()

    return [dict(r) for r in rows]