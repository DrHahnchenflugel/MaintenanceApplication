from datetime import datetime, timezone
from flask import render_template, request, abort
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
        UUID(value)
    except ValueError:
        abort(400, description=f"Invalid {name}, must be UUID")
    return value


@web_bp.get("/assets", strict_slashes=False)
def assets_index():
    status_id = parse_uuid_arg("status_id")
    site_id = parse_uuid_arg("site_id")
    category_id = parse_uuid_arg("category_id")
    make_id = parse_uuid_arg("make_id")
    model_id = parse_uuid_arg("model_id")
    variant_id = parse_uuid_arg("variant_id")
    asset_tag = (request.args.get("asset_tag") or "").strip() or None
    retired_mode = (request.args.get("retired") or "active").strip().lower()

    if retired_mode not in ("active", "retired", "all"):
        retired_mode = "active"

    if not category_id:
        make_id = model_id = variant_id = None
    elif not make_id:
        model_id = variant_id = None
    elif not model_id:
        variant_id = None

    categories = lookups.list_asset_categories()
    makes = lookups.list_makes(category_id=category_id) if category_id else []
    models = lookups.list_models(make_id=make_id) if make_id else []
    variants = lookups.list_variants(model_id=model_id) if model_id else []

    if make_id and make_id not in {m["id"] for m in makes}:
        make_id = model_id = variant_id = None
        models = []
        variants = []

    if model_id and model_id not in {m["id"] for m in models}:
        model_id = variant_id = None
        variants = []

    if variant_id and variant_id not in {v["id"] for v in variants}:
        variant_id = None

    status_options = lookups.list_asset_statuses()
    sites = site_service.list_sites()

    filters = {
        "site_id": site_id,
        "category_id": category_id,
        "status_id": status_id,
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
        retired_mode=retired_mode,
    )

    return render_template(
        "assets/viewAssets.html",
        assets=result["items"],
        categories=categories,
        makes=makes,
        models=models,
        variants=variants,
        status_options=status_options,
        sites=sites,
        cur_status_id=status_id,
        cur_site_id=site_id,
        cur_category_id=category_id,
        cur_make_id=make_id,
        cur_model_id=model_id,
        cur_variant_id=variant_id,
        cur_asset_tag=asset_tag or "",
        cur_retired_mode=retired_mode,
    )


@web_bp.get("/assets/<uuid:asset_id>", strict_slashes=False)
def view_asset(asset_id):
    asset = asset_service.get_asset_service(asset_id)
    if asset is None:
        abort(404)

    acquired_at = asset.get("acquired_at")
    asset_age = "-"
    if acquired_at:
        asset_age = human_delta_2_times(acquired_at, datetime.now(timezone.utc))

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
    )
