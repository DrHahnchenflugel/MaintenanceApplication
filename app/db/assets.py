from sqlalchemy import text
from app.db.connection import get_connection

def get_asset_row(asset_id):
    """
    Fetch a single asset row by id.

    Args:
        asset_id: integer id from the `asset` table.

    Returns:
        dict with asset columns if found, otherwise None.

        Ex:
        {
            "id": 12,
            "variant_id": 3,
            "category_id": 4,
            "site_id": 1,
            "status_id": 1,
            "serial_num": "1234567890",
            "asset_tag": "EV3-RC-11",
            "acquired_at": ...,
            "retired_at": None,
            "retire_reason": None,
            "created_at": ...,
            "updated_at": ...,
            "site_shorthand: ...,
            "site_fullname"
        }
    """

    sql = text("""
        SELECT
            id,
            variant_id,
            category_id,
            site_id,
            status_id,
            serial_num,
            asset_tag,
            acquired_at,
            retired_at,
            retire_reason,
            created_at,
            updated_at,
        FROM asset
        JOIN site ON asset.site_id = site.id
        WHERE id = :id
    """)

    with (get_connection() as conn):
        row = conn.execute(sql, {"id": asset_id})
        row = row.mappings()
        row = row.first()

    if row is None:
        return None

    return dict(row)

def list_asset_rows(
    site_id=None,
    category_id=None,
    status_id=None,
    make_id=None,
    model_id=None,
    variant_id=None,
    asset_tag=None,
    sort=None,
    limit=None,
    offset=None,
    retired_mode: str = "active",
    ):
    """
    List assets with optional filters, sorting, and pagination.
    Aassumes arguments are already validated by service / route layer.

    Args:
        site_id: filter by asset.site_id
        category_id: filter by asset.category_id
        status_id: filter by asset.status_id
        make_id: filter by make.id (via variant -> model -> make join)
        model_id: filter by model.id (via variant -> model join)
        variant_id: filter by asset.variant_id
        asset_tag: filter by exact asset_tag
        sort: list of (field_name, direction) pairs, e.g.
              [("asset_tag", "asc"), ("created_at", "desc")]
        limit: max number of rows to return (for pagination)
        offset: number of rows to skip (for pagination)
        retired_mode: view asset based on active statuses, e.g., ["active" (only), "retired" (only), all]

    Returns:
        (rows, total_count)

        rows: list of dicts, each dict is one asset row (same shape as
              get_asset_row()).

        total_count: integer number of rows that match the filters,
                     ignoring limit/offset.

    """

    # Base SELECT – join variant/model so make_id/model_id filters work.
    base_select = """
        SELECT
            asset.id,
            asset.variant_id,
            asset.category_id,
            asset.site_id,
            asset.status_id,
            asset.serial_num,
            asset.asset_tag,
            asset.acquired_at,
            asset.retired_at,
            asset.retire_reason,
            asset.created_at,
            asset.updated_at
        FROM asset
        LEFT JOIN variant ON asset.variant_id = variant.id
        LEFT JOIN model ON variant.model_id = model.id
    """

    where_clauses = []
    params = {}

    # Retired filter: "active" (default), "retired", "all"
    if retired_mode == "active":
        where_clauses.append("asset.retired_at IS NULL")
    elif retired_mode == "retired":
        where_clauses.append("asset.retired_at IS NOT NULL")
    elif retired_mode == "all":
        pass  # no clause
    else:
        # safety net; should not happen if service validates
        where_clauses.append("asset.retired_at IS NULL")

    # Direct asset filters
    if site_id is not None:
        where_clauses.append("asset.site_id = :site_id")
        params["site_id"] = site_id

    if category_id is not None:
        where_clauses.append("asset.category_id = :category_id")
        params["category_id"] = category_id

    if status_id is not None:
        where_clauses.append("asset.status_id = :status_id")
        params["status_id"] = status_id

    if variant_id is not None:
        where_clauses.append("asset.variant_id = :variant_id")
        params["variant_id"] = variant_id

    if asset_tag is not None:
        # Exact match for now
        where_clauses.append("asset.asset_tag = :asset_tag")
        params["asset_tag"] = asset_tag

    # Filters through joins
    if model_id is not None:
        where_clauses.append("model.id = :model_id")
        params["model_id"] = model_id

    if make_id is not None:
        where_clauses.append("model.make_id = :make_id")
        params["make_id"] = make_id

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    # Sorting
    # Map logical names to actual SQL columns
    sort_field_map = {
        "id": "asset.id",
        "asset_tag": "asset.asset_tag",
        "site_id": "asset.site_id",
        "category_id": "asset.category_id",
        "status_id": "asset.status_id",
        "created_at": "asset.created_at",
        "updated_at": "asset.updated_at",
    }

    # Default ordering
    order_by_sql = "ORDER BY asset.id"

    if sort:
        order_parts = []
        for field_name, direction in sort:
            col = sort_field_map.get(field_name)
            if not col:
                # Unknown field, ignore it; the service layer should avoid this anyway.
                continue

            dir_sql = "ASC"
            if isinstance(direction, str) and direction.lower() == "desc":
                dir_sql = "DESC"

            order_parts.append(f"{col} {dir_sql}")

        if order_parts:
            order_by_sql = "ORDER BY " + ", ".join(order_parts)

    # Pagination
    limit_offset_sql = ""
    if limit is not None:
        limit_offset_sql += " LIMIT :limit"
        params["limit"] = limit

    if offset is not None:
        limit_offset_sql += " OFFSET :offset"
        params["offset"] = offset

    # Final SELECT
    select_sql = text(f"""
        {base_select}
        {where_sql}
        {order_by_sql}
        {limit_offset_sql}
    """)

    # COUNT(*) with same filters, no order/limit/offset
    count_sql = text(f"""
        SELECT COUNT(*) AS total
        FROM asset
        LEFT JOIN variant ON asset.variant_id = variant.id
        LEFT JOIN model ON variant.model_id = model.id
        {where_sql}
    """)

    with get_connection() as conn:
        total_row = conn.execute(count_sql, params).mappings().first()
        total = int(total_row["total"]) if total_row is not None else 0

        result = conn.execute(select_sql, params).mappings().all()

    rows = [dict(row) for row in result]
    return rows, total

def create_asset_row(
    variant_id,
    category_id,
    site_id,
    status_id,
    serial_num=None,
    asset_tag=None,
    acquired_at=None,
):
    """
    Insert a new asset row and return the full row as a dict.

    Assumes:
      - asset.id is generated by the DB (uuid default).
      - variant_id, category_id, site_id, status_id are UUIDs (or UUID strings).
    """

    sql = text("""
        INSERT INTO asset (
            variant_id,
            category_id,
            site_id,
            status_id,
            asset_tag,
            acquired_at
        )
        VALUES (
            :variant_id,
            :category_id,
            :site_id,
            :status_id,
            :asset_tag,
            :acquired_at
        )
        RETURNING
            id,
            variant_id,
            category_id,
            site_id,
            status_id,
            serial_num,
            asset_tag,
            acquired_at,
            retired_at,
            retire_reason,
            created_at,
            updated_at
    """)

    params = {
        "variant_id": variant_id,
        "category_id": category_id,
        "site_id": site_id,
        "status_id": status_id,
        "serial_num": serial_num,
        "asset_tag": asset_tag,
        "acquired_at": acquired_at,
    }

    with get_connection() as conn:
        row = conn.execute(sql, params).mappings().first()

    if row is None:
        # Should not happen unless INSERT RETURNING returns nothing
        raise RuntimeError("Failed to insert asset")

    return dict(row)

def update_asset_row(asset_id, fields: dict):
    """
    Partially update an asset row.

    Args:
        asset_id: UUID (or string) primary key value.
        fields: dict of {column_name: value} with DB column names,
                e.g. {"site_id": ..., "status_id": ..., "asset_tag": ...}

    Returns:
        dict of the updated row, or None if asset_id not found.
    """

    if not fields:
        # Nothing to do, just return current row
        return get_asset_row(asset_id)

    set_clauses = []
    params = {"id": asset_id}

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
        UPDATE asset
        SET {set_sql}
        WHERE id = :id
        RETURNING
            id,
            variant_id,
            category_id,
            site_id,
            status_id,
            serial_num,
            asset_tag,
            acquired_at,
            retired_at,
            retire_reason,
            created_at,
            updated_at
    """)

    with get_connection() as conn:
        row = conn.execute(sql, params).mappings().first()

    if row is None:
        return None

    return dict(row)

def retire_asset_row(asset_id, retire_reason=None):
    """
    Soft-delete an asset by setting retired_at and retire_reason.

    Returns:
      dict of the updated row, or None if asset_id not found.
    """

    sql = text("""
        UPDATE asset
        SET
            retired_at = NOW(),
            retire_reason = :retire_reason,
            updated_at = NOW()
        WHERE id = :id
        RETURNING
            id,
            variant_id,
            category_id,
            site_id,
            status_id,
            serial_num,
            asset_tag,
            acquired_at,
            retired_at,
            retire_reason,
            created_at,
            updated_at
    """)

    params = {
        "id": asset_id,
        "retire_reason": retire_reason,
    }

    with get_connection() as conn:
        row = conn.execute(sql, params).mappings().first()

    if row is None:
        return None

    return dict(row)
