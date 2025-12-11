from app.db import assets as assets_repo

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
    include=None
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
        asset_id=id,
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
    )

    # For now, we just return the rows as-is.
    # Later we can add include expansions similar to get_asset_service.
    items = [dict(row) for row in rows]

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