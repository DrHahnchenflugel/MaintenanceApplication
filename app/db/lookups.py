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

def list_makes(category_id=None):
    sql = """
    SELECT id, label, category_id
    FROM make
    """

    params = {}
    if category_id:
        sql += " WHERE category_id = :category_id"
        params["category_id"] = category_id

    sql += " ORDER BY label ASC"
    
    with get_connection() as conn:
        rows = conn.execute(
            text(sql),
            {"category_id": category_id}
        ).mappings().all()
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