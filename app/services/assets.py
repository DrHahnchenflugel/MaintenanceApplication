import io
from flask import current_app
import qrcode
from app.db import assets as assets_repo
from uuid import UUID
from sqlalchemy.exc import IntegrityError

from app.services import lookups
from app.services import sites as site_service

DEFAULT_PUBLIC_BASE_URL = "http://server2-ubuntu"
QR_BOX_SIZE = 8
QR_BORDER = 4

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


def _parse_site_id_field(payload, field_name: str = "site_id", required: bool = True):
    normalized_site_id = site_service.validate_site_id(
        payload.get(field_name),
        required=required,
        field_name=field_name,
    )
    return UUID(normalized_site_id) if normalized_site_id else None


def _normalize_uuid_value(value, field_name: str, required: bool = True) -> str | None:
    if value is None or str(value).strip() == "":
        if required:
            raise ValueError(f"Missing required field: {field_name}")
        return None

    try:
        return str(UUID(str(value).strip()))
    except ValueError:
        raise ValueError(f"Invalid {field_name}, must be a UUID string")


def _normalize_asset_tag(value) -> str:
    asset_tag = (value or "").strip()
    if not asset_tag:
        raise ValueError("asset_tag is required and must be a string")
    return asset_tag


def _normalize_changed_by(value) -> str | None:
    normalized = (value or "").strip()
    if not normalized:
        return None
    return normalized


def _get_public_base_url() -> str:
    base_url = (current_app.config.get("MAINTENANCE_PUBLIC_BASE_URL") or DEFAULT_PUBLIC_BASE_URL).strip()
    if not base_url:
        return DEFAULT_PUBLIC_BASE_URL
    return base_url.rstrip("/")


def _build_qr_png_bytes(payload: str) -> bytes:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=QR_BOX_SIZE,
        border=QR_BORDER,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _validate_asset_relationships(payload: dict) -> tuple[str, str, str, str]:
    category_id = lookups.validate_category_id(
        payload.get("category_id"),
        required=True,
        field_name="category_id",
    )
    variant_id = lookups.validate_variant_id(
        payload.get("variant_id"),
        required=True,
        field_name="variant_id",
    )

    variant = lookups.get_variant(variant_id)
    resolved_model_id = variant["model_id"]

    model_id = lookups.validate_model_id(
        payload.get("model_id"),
        required=True,
        field_name="model_id",
    )
    if model_id != resolved_model_id:
        raise ValueError("Selected variant does not belong to the selected model")

    model = lookups.get_model(model_id)
    resolved_make_id = model["make_id"]

    make_id = lookups.validate_make_id(
        payload.get("make_id"),
        required=True,
        field_name="make_id",
    )
    if make_id != resolved_make_id:
        raise ValueError("Selected model does not belong to the selected make")

    make = lookups.get_make(make_id)

    if make["category_id"] != category_id:
        raise ValueError("Selected make does not belong to the selected category")

    return category_id, make_id, model_id, variant_id


def _serialize_asset_row(row: dict | None) -> dict | None:
    if row is None:
        return None

    asset = dict(row)

    if "id" in asset and asset["id"] is not None:
        asset["id"] = str(asset["id"])
        asset["asset_id"] = asset["id"]
    elif "asset_id" in asset and asset["asset_id"] is not None:
        asset["asset_id"] = str(asset["asset_id"])
        asset["id"] = asset["asset_id"]

    for field_name in ("variant_id", "category_id", "site_id", "status_id"):
        if field_name in asset and asset[field_name] is not None:
            asset[field_name] = str(asset[field_name])

    if "serial_num" in asset:
        asset["serial_number"] = asset.pop("serial_num")

    return asset


def get_asset(asset_id, include=None):
    if include is None:
        include = []

    row = assets_repo.get_asset_row(_normalize_uuid_value(asset_id, "asset_id", required=True))
    return _serialize_asset_row(row)


def get_asset_by_tag(asset_tag: str):
    tag = (asset_tag or "").strip()
    if not tag:
        return None

    row = assets_repo.get_asset_row_by_tag(tag)
    return _serialize_asset_row(row)


def list_asset_statuses():
    rows = assets_repo.list_asset_status_rows()
    items = []
    for row in rows:
        items.append(
            {
                "id": str(row["id"]),
                "code": row["code"],
                "label": row["label"],
                "display_order": row["display_order"],
            }
        )
    return items


def get_asset_status(status_id):
    normalized_status_id = _normalize_uuid_value(status_id, "status_id", required=True)
    row = assets_repo.get_asset_status_row(normalized_status_id)
    if row is None:
        return None

    return {
        "id": str(row["id"]),
        "code": row["code"],
        "label": row["label"],
        "display_order": row["display_order"],
    }


def set_asset_status(asset_id: str, to_status_id: str, changed_by: str | None = None):
    normalized_asset_id = _normalize_uuid_value(asset_id, "asset_id", required=True)
    normalized_to_status_id = _normalize_uuid_value(to_status_id, "to_status_id", required=True)

    asset = assets_repo.get_asset_row(normalized_asset_id)
    if asset is None:
        raise ValueError("Unknown asset_id")

    if assets_repo.get_asset_status_row(normalized_to_status_id) is None:
        raise ValueError("Unknown to_status_id")

    current_status_id = assets_repo.get_asset_status_id(normalized_asset_id)
    normalized_from_status_id = None if current_status_id is None else str(current_status_id)

    if normalized_from_status_id == normalized_to_status_id:
        return {
            "asset_id": normalized_asset_id,
            "changed": False,
            "from_status_id": normalized_from_status_id,
            "to_status_id": normalized_to_status_id,
        }

    updated = assets_repo.update_asset_row(
        asset_id=normalized_asset_id,
        fields={"status_id": normalized_to_status_id},
    )
    if updated is None:
        raise ValueError("Unknown asset_id")

    assets_repo.create_asset_status_history_row(
        asset_id=normalized_asset_id,
        from_status_id=normalized_from_status_id,
        to_status_id=normalized_to_status_id,
        changed_by=_normalize_changed_by(changed_by),
    )

    return {
        "asset_id": normalized_asset_id,
        "changed": True,
        "from_status_id": normalized_from_status_id,
        "to_status_id": normalized_to_status_id,
    }

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

    asset = get_asset(asset_id, include=include)
    if asset is None:
        return None

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


def get_asset_qr_target_url_service(asset_id) -> str | None:
    asset = get_asset_service(asset_id)
    if asset is None:
        return None

    return f"{_get_public_base_url()}/assets/{asset['asset_id']}"


def get_asset_qr_png_service(asset_id) -> bytes | None:
    target_url = get_asset_qr_target_url_service(asset_id)
    if target_url is None:
        return None

    return _build_qr_png_bytes(target_url)

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
    items = [_serialize_asset_row(row) for row in rows]


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
      - make_id (UUID string, required)
      - model_id (UUID string, required)
      - status_id (UUID string, required)
      - variant_id (UUID string, required)
      - serial_number (str, optional)
      - acquired_at (ISO datetime string, optional; passed through to DB)

    Returns:
      dict representing the created asset row.
    """

    asset_tag = _normalize_asset_tag(payload.get("asset_tag"))
    if assets_repo.asset_tag_exists(asset_tag):
        raise ValueError("asset_tag already exists")

    site_id = site_service.validate_site_id(
        payload.get("site_id"),
        required=True,
        field_name="site_id",
    )
    category_id, _make_id, _model_id, variant_id = _validate_asset_relationships(payload)
    status_id = lookups.validate_asset_status_id(
        payload.get("status_id"),
        required=True,
        field_name="status_id",
    )

    # Optional fields
    acquired_at = payload.get("acquired_at")      # let Postgres cast if given

    # Call L3 to actually insert
    try:
        row = assets_repo.create_asset_row(
            variant_id=variant_id,
            category_id=category_id,
            site_id=site_id,
            status_id=status_id,
            asset_tag=asset_tag,
            acquired_at=acquired_at,
        )
    except IntegrityError as exc:
        raise ValueError("Unable to create asset with the supplied values") from exc

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
    requested_status_id = None

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
        update_fields["site_id"] = _parse_site_id_field(payload, "site_id", required=False)

    if "category_id" in payload:
        update_fields["category_id"] = _parse_uuid_field(payload, "category_id", required=False)

    if "status_id" in payload:
        requested_status_id = lookups.validate_asset_status_id(
            payload.get("status_id"),
            required=False,
            field_name="status_id",
        )
        if requested_status_id is None:
            raise ValueError("status_id is required")

    if "variant_id" in payload:
        update_fields["variant_id"] = _parse_uuid_field(payload, "variant_id", required=False)

    # Datetime-ish fields – let Postgres cast from string
    if "acquired_at" in payload:
        update_fields["acquired_at"] = payload["acquired_at"]

    if "retired_at" in payload:
        update_fields["retired_at"] = payload["retired_at"]

    if not update_fields and "status_id" not in payload:
        raise ValueError("No valid fields to update")

    normalized_asset_id = str(asset_id)

    if update_fields:
        row = assets_repo.update_asset_row(asset_id=asset_id, fields=update_fields)
        if row is None:
            return None
    else:
        row = assets_repo.get_asset_row(normalized_asset_id)
        if row is None:
            return None

    if "status_id" in payload:
        set_asset_status(
            asset_id=normalized_asset_id,
            to_status_id=requested_status_id,
            changed_by=payload.get("changed_by"),
        )

    return get_asset_service(normalized_asset_id)

def retire_asset_service(asset_id: UUID, retire_reason: str | None = None) -> bool:
    """
    Mark an asset as retired.

    Returns:
      True  if an asset was updated
      False if no such asset_id exists
    """
    row = assets_repo.retire_asset_row(asset_id=asset_id, retire_reason=retire_reason)
    return row is not None
