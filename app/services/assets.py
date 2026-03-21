from app.db import assets as assets_repo
from uuid import UUID

def _parse_uuid_field(payload, field_name: str, required: bool = True):
    value = payload.get(field_name)
    if value is None:
        if required:
            raise ValueError(f"Missing required field: {field_name}")
        return None
    try:
        return UUID(value)
    except ValueError:
        raise ValueError(f"Invalid {field_name}, must be a UUID string")

def get_asset_service(asset_id, include=None):
    """
    Get a single asset by id, with optional expansions.

    Args:
        asset_id: integer id of the asset.
        include: iterable of strings, e.g. ["site", "category", "status", "variant"]

    Returns:
        dict representing the asset, possibly with extra keys for includes.

    Raises:
        Nothing. If not found, returns None and the route layer decides it's a 404.
    """

    if include is None:
        include = []

    include_set = set(include)

    # Base row from L3
    row = assets_repo.get_asset_row(asset_id)
    if row is None:
        return None

    # Right now row is just the asset table columns.
    asset = dict(row)

    # normalize names
    asset["asset_id"] = asset.pop("id")
    asset["serial_number"] = asset.pop("serial_num")

    # --- Includes (commented out until db.lookups ready) ---

    # if "site" in include_set and asset.get("site_id") is not None:
    #     site = lookups_repo.get_site_row(asset["site_id"])
    #     asset["site"] = site
    #
    # if "category" in include_set and asset.get("category_id") is not None:
    #     category = lookups_repo.get_category_row(asset["category_id"])
    #     asset["category"] = category
    #
    # if "status" in include_set and asset.get("status_id") is not None:
    #     status = lookups_repo.get_asset_status_row(asset["status_id"])
    #     asset["status"] = status
    #
    # if "variant" in include_set and asset.get("variant_id") is not None:
    #     variant = lookups_repo.get_variant_row(asset["variant_id"])
    #     asset["variant"] = variant

    return asset

def list_assets_service(
    filters,
    sort,
    page,
    page_size,
    include=None,
    retired_mode: str = "active",
    ):
    """
    List assets with filters/sorting/pagination and optional expansions.

    Args:
        filters: dict of simple filter values, e.g.
                 {
                   "site_id": 1,
                   "category_id": None,
                   "status_id": 2,
                   "make_id": None,
                   "model_id": None,
                   "variant_id": None,
                   "asset_tag": None,
                 }
                 All keys are optional; missing/None = no filter.

        sort: list of (field_name, direction) pairs, e.g.
              [("asset_tag", "asc"), ("created_at", "desc")]
              Route layer is responsible for parsing "?sort=..." into this.

        page: 1-based page number (int)
        page_size: number of items per page (int)
        include: iterable of include strings, e.g. ["site", "category"]
        retired_mode: view asset based on active statuses, e.g., ["active" (only), "retired" (only), all]

    Returns:
        dict:
        {
          "items": [ {asset...}, ... ],
          "page": page,
          "page_size": page_size,
          "total": total_count
        }
    """

    if include is None:
        include = []

    include_set = set(include)

    # Translate page/page_size into limit/offset for L3
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1

    limit = page_size
    offset = (page - 1) * page_size

    # Call L3 with unpacked filters
    rows, total = assets_repo.list_asset_rows(
        site_id=filters.get("site_id"),
        category_id=filters.get("category_id"),
        status_id=filters.get("status_id"),
        make_id=filters.get("make_id"),
        model_id=filters.get("model_id"),
        variant_id=filters.get("variant_id"),
        asset_tag=filters.get("asset_tag"),
        sort=sort,
        limit=limit,
        offset=offset,
        retired_mode=retired_mode,
    )

    # For now, we just return the rows as-is.
    # Later we can add include expansions similar to get_asset_service.
    items = []
    for row in rows:
        asset = dict(row)
        asset["asset_id"] = asset.pop("id")
        asset["serial_number"] = asset.pop("serial_num")
        items.append(asset)


    # --- Includes (optional future step) ---
    # If you want "include=site,category" for lists too, this is where you'd:
    #  - collect all site_ids/category_ids from items
    #  - call lookups_repo.get_sites_by_ids(site_ids)
    #  - attach site/category dicts onto each item

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
    }

def create_asset_service(payload: dict) -> dict:
    """
    Create a new asset.

    Expected payload keys (JSON):
      - asset_tag (str, required)
      - site_id (UUID string, required)
      - category_id (UUID string, required)
      - status_id (UUID string, required)
      - variant_id (UUID string, required)
      - serial_number (str, optional)
      - acquired_at (ISO datetime string, optional; passed through to DB)

    Returns:
      dict representing the created asset row.
    """

    # Required simple fields
    asset_tag = payload.get("asset_tag")
    if not asset_tag or not isinstance(asset_tag, str):
        raise ValueError("asset_tag is required and must be a string")

    # UUID fields
    site_id = _parse_uuid_field(payload, "site_id", required=True)
    category_id = _parse_uuid_field(payload, "category_id", required=True)
    status_id = _parse_uuid_field(payload, "status_id", required=True)
    variant_id = _parse_uuid_field(payload, "variant_id", required=True)

    # Optional fields
    acquired_at = payload.get("acquired_at")      # let Postgres cast if given

    # Call L3 to actually insert
    row = assets_repo.create_asset_row(
        variant_id=variant_id,
        category_id=category_id,
        site_id=site_id,
        status_id=status_id,
        asset_tag=asset_tag,
        acquired_at=acquired_at,
    )

    return row

def patch_asset_service(asset_id: UUID, payload: dict) -> dict | None:
    """
    Partially update an asset.

    Allowed fields in payload:
      - asset_tag (str)
      - serial_number (str)
      - site_id (UUID string)
      - category_id (UUID string)
      - status_id (UUID string)
      - variant_id (UUID string)
      - acquired_at (ISO datetime string)
      - retired_at (ISO datetime string)
      - retire_reason (str)
    """

    update_fields: dict[str, object] = {}

    # Simple string fields
    if "asset_tag" in payload:
        value = payload["asset_tag"]
        if value is not None and not isinstance(value, str):
            raise ValueError("asset_tag must be a string or null")
        update_fields["asset_tag"] = value

    if "serial_number" in payload:
        value = payload["serial_number"]
        if value is not None and not isinstance(value, str):
            raise ValueError("serial_number must be a string or null")
        update_fields["serial_num"] = value  # DB column name

    if "retire_reason" in payload:
        value = payload["retire_reason"]
        if value is not None and not isinstance(value, str):
            raise ValueError("retire_reason must be a string or null")
        update_fields["retire_reason"] = value

    # UUID fields (optional; only parsed if present)
    if "site_id" in payload:
        update_fields["site_id"] = _parse_uuid_field(payload, "site_id", required=False)

    if "category_id" in payload:
        update_fields["category_id"] = _parse_uuid_field(payload, "category_id", required=False)

    if "status_id" in payload:
        update_fields["status_id"] = _parse_uuid_field(payload, "status_id", required=False)

    if "variant_id" in payload:
        update_fields["variant_id"] = _parse_uuid_field(payload, "variant_id", required=False)

    # Datetime-ish fields – let Postgres cast from string
    if "acquired_at" in payload:
        update_fields["acquired_at"] = payload["acquired_at"]

    if "retired_at" in payload:
        update_fields["retired_at"] = payload["retired_at"]

    if not update_fields:
        raise ValueError("No valid fields to update")

    row = assets_repo.update_asset_row(asset_id=asset_id, fields=update_fields)
    # row is dict or None
    return row

def retire_asset_service(asset_id: UUID, retire_reason: str | None = None) -> bool:
    """
    Mark an asset as retired.

    Returns:
      True  if an asset was updated
      False if no such asset_id exists
    """
    row = assets_repo.retire_asset_row(asset_id=asset_id, retire_reason=retire_reason)
    return row is not None