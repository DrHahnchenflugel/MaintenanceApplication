from sqlalchemy import text
from app.db.connection import get_connection

def list_issue_rows(
    site_id=None,
    asset_id=None,
    status_id=None,
    reported_by=None,
    created_from=None,
    created_to=None,
    closed_mode: str = "open",   # "open", "closed", "all"
    search=None,
    sort=None,
    limit=None,
    offset=None,
):
    """
    List issues with optional filters, sorting, and pagination.
    """

    base_select = """
        SELECT
            issue.id,
            issue.asset_id,
            issue.status_id,
            issue.title,
            issue.description,
            issue.reported_by,
            issue.created_at,
            issue.updated_at,
            issue.closed_at,

            asset.asset_tag,
            asset.site_id,

            issue_status.code AS status_code,
            issue_status.label AS status_label,

            last_action.last_action_at,
            last_action.last_action_type_code,
            last_action.last_action_type_label
        FROM issue
        JOIN issue_status
          ON issue.status_id = issue_status.id
        JOIN asset
          ON issue.asset_id = asset.id
        LEFT JOIN LATERAL (
            SELECT
                ia.created_at     AS last_action_at,
                at.code           AS last_action_type_code,
                at.label          AS last_action_type_label
            FROM issue_action ia
            JOIN action_type at
              ON ia.action_type_id = at.id
            WHERE ia.issue_id = issue.id
            ORDER BY ia.created_at DESC
            LIMIT 1
        ) AS last_action ON TRUE
    """

    where_clauses = []
    params = {}

    # Closed filter
    if closed_mode == "open":
        where_clauses.append("issue.closed_at IS NULL")
    elif closed_mode == "closed":
        where_clauses.append("issue.closed_at IS NOT NULL")
    elif closed_mode == "all":
        pass
    else:
        where_clauses.append("issue.closed_at IS NULL")

    # Direct filters
    if asset_id is not None:
        where_clauses.append("issue.asset_id = :asset_id")
        params["asset_id"] = asset_id

    if status_id is not None:
        where_clauses.append("issue.status_id = :status_id")
        params["status_id"] = status_id

    if reported_by is not None:
        where_clauses.append("issue.reported_by = :reported_by")
        params["reported_by"] = reported_by

    if created_from is not None:
        where_clauses.append("issue.created_at >= :created_from")
        params["created_from"] = created_from

    if created_to is not None:
        where_clauses.append("issue.created_at <= :created_to")
        params["created_to"] = created_to

    if site_id is not None:
        where_clauses.append("asset.site_id = :site_id")
        params["site_id"] = site_id

    if search is not None and search != "":
        where_clauses.append(
            "(issue.title ILIKE :search OR issue.description ILIKE :search)"
        )
        params["search"] = f"%{search}%"

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    sort_field_map = {
        "id": "issue.id",
        "created_at": "issue.created_at",
        "updated_at": "issue.updated_at",
        "title": "issue.title",
        "status_id": "issue.status_id",
        "site_id": "asset.site_id",
    }

    order_by_sql = "ORDER BY issue.created_at DESC"

    if sort:
        order_parts = []
        for field_name, direction in sort:
            col = sort_field_map.get(field_name)
            if not col:
                continue

            dir_sql = "ASC"
            if isinstance(direction, str) and direction.lower() == "desc":
                dir_sql = "DESC"

            order_parts.append(f"{col} {dir_sql}")

        if order_parts:
            order_by_sql = "ORDER BY " + ", ".join(order_parts)

    limit_offset_sql = ""
    if limit is not None:
        limit_offset_sql += " LIMIT :limit"
        params["limit"] = limit

    if offset is not None:
        limit_offset_sql += " OFFSET :offset"
        params["offset"] = offset

    select_sql = text(f"""
        {base_select}
        {where_sql}
        {order_by_sql}
        {limit_offset_sql}
    """)

    count_sql = text(f"""
        SELECT COUNT(*) AS total
        FROM issue
        JOIN asset
          ON issue.asset_id = asset.id
        {where_sql}
    """)

    with get_connection() as conn:
        total_row = conn.execute(count_sql, params).mappings().first()
        total = int(total_row["total"]) if total_row is not None else 0

        result = conn.execute(select_sql, params).mappings().all()

    rows = [dict(row) for row in result]
    return rows, total

def get_issue_row(issue_id):
    """
    Fetch a single issue row by id, with joined status/asset info and last action.

    Returns:
        dict with keys:
          - id, asset_id, status_id, title, description, reported_by,
            created_at, updated_at, closed_at
          - asset_tag, site_id
          - status_code, status_label
          - last_action_at, last_action_type_code, last_action_type_label
        or None if not found.
    """

    sql = text("""
        SELECT
            issue.id,
            issue.asset_id,
            issue.status_id,
            issue.title,
            issue.description,
            issue.reported_by,
            issue.created_at,
            issue.updated_at,
            issue.closed_at,

            asset.asset_tag,
            asset.site_id,

            issue_status.code  AS status_code,
            issue_status.label AS status_label,

            last_action.last_action_at,
            last_action.last_action_type_code,
            last_action.last_action_type_label
        FROM issue
        JOIN issue_status
          ON issue.status_id = issue_status.id
        JOIN asset
          ON issue.asset_id = asset.id
        LEFT JOIN LATERAL (
            SELECT
                ia.created_at AS last_action_at,
                at.code       AS last_action_type_code,
                at.label      AS last_action_type_label
            FROM issue_action ia
            JOIN action_type at
              ON ia.action_type_id = at.id
            WHERE ia.issue_id = issue.id
            ORDER BY ia.created_at DESC
            LIMIT 1
        ) AS last_action ON TRUE
        WHERE issue.id = :id
    """)

    with get_connection() as conn:
        row = conn.execute(sql, {"id": issue_id}).mappings().first()

    if row is None:
        return None

    return dict(row)
