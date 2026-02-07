from flask import render_template, request, abort
from . import bp as web_bp
from uuid import UUID
from app.services import assets as asset_service
from app.services import lookups
from app.services import sites as site_service


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
