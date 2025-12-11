from sqlalchemy import text
from app.db.connection import get_connection


def count_issues_by_status_codes_row(status_codes):
    """
    Low-level helper: count issues whose status code is in the provided list.

    status_codes: list/tuple of strings, e.g. ("OPEN", "IN_PROGRESS")
    Returns: integer count
    """
    if not status_codes:
        return 0

    # Build placeholders: :code_0, :code_1, ...
    placeholders = []
    params = {}

    index = 0
    for code in status_codes:
        key = f"code_{index}"
        placeholders.append(f":{key}")
        params[key] = code
        index += 1

    placeholders_sql = ", ".join(placeholders)

    sql = text(f"""
        SELECT COUNT(*) AS total
        FROM issue i
        JOIN issue_status s ON i.status_id = s.id
        WHERE s.code IN ({placeholders_sql})
    """)

    with get_connection() as conn:
        row = conn.execute(sql, params).mappings().first()

    if row is None:
        return 0

    return int(row["total"])

def get_oldest_issue_by_status_codes_row(status_codes):
    """
    Low-level helper: get the oldest issue (by created_at ASC) for given status codes.

    status_codes: list/tuple of strings, e.g. ("OPEN", "IN_PROGRESS")
    Returns:
        dict with keys {"id", "created_at"} or None
    """
    if not status_codes:
        return None

    placeholders = []
    params = {}

    index = 0
    for code in status_codes:
        key = f"code_{index}"
        placeholders.append(f":{key}")
        params[key] = code
        index += 1

    placeholders_sql = ", ".join(placeholders)

    sql = text(f"""
        SELECT
            i.id,
            i.created_at
        FROM issue i
        JOIN issue_status s ON i.status_id = s.id
        WHERE s.code IN ({placeholders_sql})
        ORDER BY i.created_at ASC
        LIMIT 1
    """)

    with get_connection() as conn:
        row = conn.execute(sql, params).mappings().first()

    if row is None:
        return None

    return {
        "id": row["id"],
        "created_at": row["created_at"],
    }
