from datetime import datetime, timezone
from flask import render_template, request, abort, redirect, url_for
from . import bp as web_bp
from uuid import UUID
from app.services import assets as asset_service
from app.services import lookups
from app.services import sites as site_service
from app.services import issues as issue_service
from app.helpers import human_delta_2_times


def parse_uuid_arg(name: str):
    value = (request.args.get(name) or "").strip()
    if not value:
        return None
    try:
        return str(UUID(value))
    except ValueError:
        abort(400, description=f"Invalid {name}, must be UUID")


def parse_site_filter_arg(name: str = "site_id"):
    if name not in request.args:
        return False, None

    raw_value = (request.args.get(name) or "").strip()
    if not raw_value:
        return True, None

    try:
        return True, site_service.validate_site_id(raw_value, required=True, field_name=name)
    except ValueError as exc:
        abort(400, description=str(exc))


def _normalize_uuid_rows(rows, *field_names):
    normalized_rows = []
    for row in rows:
        item = dict(row)
        for field_name in field_names:
            if field_name in item and item[field_name] is not None:
                item[field_name] = str(item[field_name])
        normalized_rows.append(item)
    return normalized_rows


def _build_asset_filter_query_params(
    *,
    site_id=None,
    include_site=False,
    category_id=None,
    make_id=None,
    model_id=None,
    variant_id=None,
    active_mode="active",
    asset_tag=None,
    include_active=False,
):
    params = {}

    if include_site:
        params["site_id"] = site_id or ""
    if category_id:
        params["category_id"] = category_id
    if make_id:
        params["make_id"] = make_id
    if model_id:
        params["model_id"] = model_id
    if variant_id:
        params["variant_id"] = variant_id
    if include_active or active_mode != "active":
        params["active"] = active_mode
    if asset_tag:
        params["asset_tag"] = asset_tag

    return params


@web_bp.get("/assets", strict_slashes=False)
def assets_index():
    site_filter_was_explicit, requested_site_id = parse_site_filter_arg("site_id")
    requested_category_id = parse_uuid_arg("category_id")
    requested_make_id = parse_uuid_arg("make_id")
    requested_model_id = parse_uuid_arg("model_id")
    requested_variant_id = parse_uuid_arg("variant_id")

    current_site = site_service.get_current_site()
    site_id = requested_site_id if site_filter_was_explicit else ((current_site or {}).get("id"))
    category_id = requested_category_id
    make_id = requested_make_id
    model_id = requested_model_id
    variant_id = requested_variant_id

    asset_tag = (request.args.get("asset_tag") or "").strip() or None
    raw_active_mode = (request.args.get("active") or request.args.get("retired") or "active").strip().lower()
    active_mode = raw_active_mode if raw_active_mode in ("active", "retired", "all") else "active"

    categories = _normalize_uuid_rows(lookups.list_asset_categories(), "id")
    makes = _normalize_uuid_rows(
        lookups.list_makes(category_id=category_id) if category_id else lookups.list_makes(),
        "id",
        "category_id",
    )

    # Category narrows the make list, but make itself stays selectable even when
    # category is blank.
    if make_id and make_id not in {make["id"] for make in makes}:
        make_id = None
        variant_id = None
        model_id = None

    if not make_id:
        model_id = variant_id = None

    models = _normalize_uuid_rows(
        lookups.list_models(make_id=make_id) if make_id else [],
        "id",
    )
    if model_id and model_id not in {model["id"] for model in models}:
        model_id = None
        variant_id = None

    if not model_id:
        variant_id = None

    variants = _normalize_uuid_rows(
        lookups.list_variants(model_id=model_id) if model_id else [],
        "id",
    )
    if variant_id and variant_id not in {variant["id"] for variant in variants}:
        variant_id = None

    include_active_param = "active" in request.args or "retired" in request.args
    requested_params = _build_asset_filter_query_params(
        site_id=requested_site_id,
        include_site=site_filter_was_explicit,
        category_id=requested_category_id,
        make_id=requested_make_id,
        model_id=requested_model_id,
        variant_id=requested_variant_id,
        active_mode=active_mode,
        asset_tag=asset_tag,
        include_active="active" in request.args,
    )
    effective_params = _build_asset_filter_query_params(
        site_id=requested_site_id,
        include_site=site_filter_was_explicit,
        category_id=category_id,
        make_id=make_id,
        model_id=model_id,
        variant_id=variant_id,
        active_mode=active_mode,
        asset_tag=asset_tag,
        include_active=include_active_param,
    )

    # Redirect once to the cleaned query string if we dropped invalid dependent
    # ids or converted legacy params like ?retired=... / ?status_id=...
    if (
        requested_params != effective_params
        or "retired" in request.args
        or "status_id" in request.args
        or ("active" in request.args and raw_active_mode not in ("active", "retired", "all"))
    ):
        return redirect(url_for("app.assets_index", **effective_params))

    status_options = _normalize_uuid_rows(lookups.list_asset_statuses(), "id")

    filters = {
        "site_id": site_id,
        "category_id": category_id,
        "make_id": make_id,
        "model_id": model_id,
        "variant_id": variant_id,
        "asset_tag": asset_tag,
    }

    result = asset_service.list_assets_service(
        filters=filters,
        sort=[("asset_tag", "asc")],
        page=1,
        page_size=200,
        include=[],
        retired_mode=active_mode,
    )

    assets = _normalize_uuid_rows(
        result["items"],
        "asset_id",
        "category_id",
        "site_id",
        "status_id",
        "variant_id",
    )

    return render_template(
        "assets/viewAssets.html",
        assets=assets,
        categories=categories,
        makes=makes,
        models=models,
        variants=variants,
        status_options=status_options,
        cur_site_id=site_id,
        cur_category_id=category_id,
        cur_make_id=make_id,
        cur_model_id=model_id,
        cur_variant_id=variant_id,
        cur_asset_tag=asset_tag or "",
        cur_active_mode=active_mode,
    )


@web_bp.get("/assets/<uuid:asset_id>", strict_slashes=False)
def view_asset(asset_id):
    asset = asset_service.get_asset_service(asset_id)
    if asset is None:
        abort(404)

    acquired_at = asset.get("acquired_at")
    asset_age = "-"
    if acquired_at:
        asset_age = human_delta_2_times(acquired_at, datetime.now(timezone.utc).date())

    issue_result = issue_service.list_issues(
        page=1,
        page_size=10,
        filters={
            "site_id": None,
            "asset_id": str(asset_id),
            "status_id": None,
            "reported_by": None,
            "created_from": None,
            "created_to": None,
            "search": None,
            "category_id": None,
            "make_id": None,
            "model_id": None,
            "variant_id": None,
            "active_status_ids": None,
        },
    )

    past_actions = issue_result["items"]

    return render_template(
        "assets/specific_asset.html",
        asset=asset,
        asset_age=asset_age,
        past_actions=past_actions,
        asset_qr_image_url=url_for("api_v2.get_asset_qr_png", asset_id=asset["asset_id"]),
    )
