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