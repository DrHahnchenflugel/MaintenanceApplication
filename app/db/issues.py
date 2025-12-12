from sqlalchemy import text
from app.db.connection import get_connection

def get_action_type_id_by_code(code: str):
    """
    Return the id from action_type for a given code, or None if not found.
    """
    sql = text("""
        SELECT id
        FROM action_type
        WHERE code = :code
    """)

    with get_connection() as conn:
        row = conn.execute(sql, {"code": code}).mappings().first()

    if row is None:
        return None

    return row["id"]

def get_issue_status_id_by_code(code: str):
    sql = text("""
        SELECT id
        FROM issue_status
        WHERE code = :code
    """)
    with get_connection() as conn:
        row = conn.execute(sql, {"code": code}).mappings().first()
    if row is None:
        return None
    return row["id"]

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

def list_issue_actions(issue_id):
    """
    Return all actions for a given issue, oldest first.

    Each row:
      - id
      - action_type_id
      - action_type_code
      - action_type_label
      - body
      - created_at
      - created_by
    """

    sql = text("""
        SELECT
            ia.id,
            ia.action_type_id,
            at.code  AS action_type_code,
            at.label AS action_type_label,
            ia.body,
            ia.created_at,
            ia.created_by
        FROM issue_action ia
        JOIN action_type at
          ON ia.action_type_id = at.id
        WHERE ia.issue_id = :issue_id
        ORDER BY ia.created_at DESC
    """)

    with get_connection() as conn:
        rows = conn.execute(sql, {"issue_id": issue_id}).mappings().all()

    return [dict(r) for r in rows]

def create_issue_row(
    asset_id,
    status_id,
    title,
    description,
    reported_by,
):
    """
    Insert a new issue row and return the full row as a dict.
    """

    sql = text("""
        INSERT INTO issue (
            asset_id,
            status_id,
            title,
            description,
            reported_by
        )
        VALUES (
            :asset_id,
            :status_id,
            :title,
            :description,
            :reported_by
        )
        RETURNING
            id,
            asset_id,
            status_id,
            title,
            description,
            reported_by,
            created_at,
            updated_at,
            closed_at
    """)

    params = {
        "asset_id": asset_id,
        "status_id": status_id,
        "title": title,
        "description": description,
        "reported_by": reported_by,
    }

    with get_connection() as conn:
        row = conn.execute(sql, params).mappings().first()

    if row is None:
        raise RuntimeError("Failed to insert issue")

    return dict(row)

def create_issue_action_row(
    issue_id,
    action_type_id,
    body,
    created_by,
):
    """
    Insert a new issue_action row.
    """

    sql = text("""
        INSERT INTO issue_action (
            issue_id,
            action_type_id,
            body,
            created_at,
            created_by
        )
        VALUES (
            :issue_id,
            :action_type_id,
            :body,
            NOW(),
            :created_by
        )
        RETURNING
            id,
            issue_id,
            action_type_id,
            body,
            created_at,
            created_by
    """)

    params = {
        "issue_id": issue_id,
        "action_type_id": action_type_id,
        "body": body,
        "created_by": created_by,
    }

    with get_connection() as conn:
        row = conn.execute(sql, params).mappings().first()

    if row is None:
        raise RuntimeError("Failed to insert issue_action")

    return dict(row)

def create_issue_status_history_row(
    issue_id,
    from_status_id,
    to_status_id,
    changed_by,
):
    """
    Insert into issue_status_history. from_status_id can be None for initial.
    """

    sql = text("""
        INSERT INTO issue_status_history (
            issue_id,
            from_status_id,
            to_status_id,
            changed_at,
            changed_by
        )
        VALUES (
            :issue_id,
            :from_status_id,
            :to_status_id,
            NOW(),
            :changed_by
        )
    """)

    params = {
        "issue_id": issue_id,
        "from_status_id": from_status_id,
        "to_status_id": to_status_id,
        "changed_by": changed_by,
    }

    with get_connection() as conn:
        conn.execute(sql, params)

def get_issue_status_id(issue_id):
    """
    Return the current status_id for a given issue, or None if the issue
    does not exist.

    Args:
        issue_id: UUID (or UUID string) of the issue.

    Returns:
        status_id (UUID) or None.
    """
    sql = text("""
        SELECT status_id
        FROM issue
        WHERE id = :id
    """)

    with get_connection() as conn:
        row = conn.execute(sql, {"id": issue_id}).mappings().first()

    if row is None:
        return None

    return row["status_id"]

def update_issue_row(issue_id, fields: dict):
    """
    Partially update an issue row.

    Args:
        issue_id: UUID (or string) primary key value.
        fields: dict of {column_name: value} with DB column names,
                e.g. {"status_id": ..., "title": ..., "description": ...}

    Returns:
        dict of the updated row, or None if issue_id not found.
    """

    if not fields:
        # Nothing to update – just return current row
        return get_issue_row(issue_id)

    set_clauses = []
    params = {"id": issue_id}

    idx = 0
    for col, value in fields.items():
        param_name = f"v_{idx}"
        set_clauses.append(f"{col} = :{param_name}")
        params[param_name] = value
        idx += 1

    # Always bump updated_at
    set_clauses.append("updated_at = NOW()")

    set_sql = ", ".join(set_clauses)

    sql = text(f"""
        UPDATE issue
        SET {set_sql}
        WHERE id = :id
        RETURNING
            id,
            asset_id,
            status_id,
            title,
            description,
            reported_by,
            created_at,
            updated_at,
            closed_at
    """)

    with get_connection() as conn:
        row = conn.execute(sql, params).mappings().first()

    if row is None:
        return None

    return dict(row)

def list_issue_status_history(issue_id):
    """
    Return all status history entries for a given issue, oldest first.

    Each row:
      - id
      - from_status_id, from_status_code, from_status_label (may be None)
      - to_status_id,   to_status_code,   to_status_label
      - changed_at
      - changed_by
    """

    sql = text("""
        SELECT
            ish.id,
            ish.from_status_id,
            fs.code  AS from_status_code,
            fs.label AS from_status_label,
            ish.to_status_id,
            ts.code  AS to_status_code,
            ts.label AS to_status_label,
            ish.changed_at,
            ish.changed_by
        FROM issue_status_history ish
        LEFT JOIN issue_status fs
          ON ish.from_status_id = fs.id
        JOIN issue_status ts
          ON ish.to_status_id = ts.id
        WHERE ish.issue_id = :issue_id
        ORDER BY ish.changed_at DESC
    """)

    with get_connection() as conn:
        rows = conn.execute(sql, {"issue_id": issue_id}).mappings().all()

    return [dict(r) for r in rows]

def list_issue_status_rows():
    """
    List all issue_status rows ordered for display.
    """
    sql = text("""
        SELECT
            id,
            code,
            label,
            display_order
        FROM issue_status
        ORDER BY display_order ASC, code ASC
    """)

    with get_connection() as conn:
        rows = conn.execute(sql).mappings().all()

    return [dict(r) for r in rows]

def list_action_type_rows():
    """
    List all action_type rows ordered for display.
    """
    sql = text("""
        SELECT
            id,
            code,
            label,
            display_order
        FROM action_type
        ORDER BY display_order ASC, code ASC
    """)

    with get_connection() as conn:
        rows = conn.execute(sql).mappings().all()

    return [dict(r) for r in rows]

def create_issue_status_row(code: str, label: str, display_order: int):
    """
    Insert a new issue_status row and return it as a dict.
    """

    sql = text("""
        INSERT INTO issue_status (
            code,
            label,
            display_order
        )
        VALUES (
            :code,
            :label,
            :display_order
        )
        RETURNING
            id,
            code,
            label,
            display_order
    """)

    params = {
        "code": code,
        "label": label,
        "display_order": display_order,
    }

    with get_connection() as conn:
        try:
            row = conn.execute(sql, params).mappings().first()
        except IntegrityError as e:
            # Check if it's the unique constraint on code
            if "issue_status_code_key" in str(e.orig):
                raise ValueError("Duplicate code for issue_status")
            raise

    if row is None:
        raise RuntimeError("Failed to insert issue_status")

    return dict(row)

def create_action_type_row(code: str, label: str, display_order: int | None = None):
    """
    Insert a new action_type row and return it as a dict.
    """

    sql = text("""
        INSERT INTO action_type (
            code,
            label,
            display_order
        )
        VALUES (
            :code,
            :label,
            :display_order
        )
        RETURNING
            id,
            code,
            label,
            display_order
    """)

    params = {
        "code": code,
        "label": label,
        "display_order": display_order,
    }

    with get_connection() as conn:
        try:
            row = conn.execute(sql, params).mappings().first()
        except IntegrityError as e:
            # Check if it's the unique constraint on code
            if "issue_status_code_key" in str(e.orig):
                raise ValueError("Duplicate code for action_type")
            raise

    if row is None:
        raise RuntimeError("Failed to insert action_type")

    return dict(row)

def get_issue_attachment_by_issue_id(issue_id: str):
    sql = text("""
        SELECT
            id,
            issue_id,
            filepath,
            content_type
        FROM issue_attachment
        WHERE issue_id = :issue_id
        LIMIT 1
    """)

    with get_connection() as conn:
        row = conn.execute(sql, {"issue_id": issue_id}).mappings().first()

    if row is None:
        return None

    return dict(row)

def create_issue_attachment(
    issue_id: str,
    filepath: str,
    content_type: str,
):
    sql = text("""
        INSERT INTO issue_attachment (
            issue_id,
            filepath,
            content_type,
            created_at
        )
        VALUES (
            :issue_id,
            :filepath,
            :content_type,
            NOW()
        )
        RETURNING
            id,
            issue_id,
            filepath,
            content_type
    """)

    with get_connection() as conn:
        row = conn.execute(
            sql,
            {
                "issue_id": issue_id,
                "filepath": filepath,
                "content_type": content_type,
            },
        ).mappings().first()

    if row is None:
        raise RuntimeError("Failed to create issue_attachment")

    return dict(row)

def list_accepted_attachment_content_types():
    sql = text("""
        SELECT content_type
        FROM accepted_attachment_content_type
    """)

    with get_connection() as conn:
        rows = conn.execute(sql).mappings().all()

    return [r["content_type"] for r in rows]

def create_accepted_attachment_content_type(content_type: str):
    sql = text("""
        INSERT INTO accepted_attachment_content_type (
            content_type
        )
        VALUES (
            :content_type
        )
        RETURNING
            id,
            content_type
    """)

    with get_connection() as conn:
        try:
            row = conn.execute(
                sql,
                {"content_type": content_type},
            ).mappings().first()
        except Exception as e:
            # rely on DB unique constraint
            raise

    if row is None:
        raise RuntimeError("Failed to insert accepted_attachment_content_type")

    return dict(row)

def delete_accepted_attachment_content_type(content_type: str):
    sql = text("""
        DELETE FROM accepted_attachment_content_type
        WHERE content_type = :content_type
    """)

    with get_connection() as conn:
        result = conn.execute(sql, {"content_type": content_type})

    return result.rowcount > 0
