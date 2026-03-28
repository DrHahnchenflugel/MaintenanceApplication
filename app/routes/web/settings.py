from flask import redirect, render_template, request, url_for
from uuid import UUID

from app.services import assets as asset_service
from app.services import auth as auth_service
from app.services import lookups
from app.services import sites as site_service

from . import bp as web_bp


def _settings_unlocked() -> bool:
    return auth_service.is_settings_admin_unlocked()


def _render_settings(template_name: str, *, active_tab: str, **context):
    return render_template(
        template_name,
        settings_unlocked=_settings_unlocked(),
        settings_active_tab=active_tab,
        **context,
    )


def _clean_form_value(name: str, default: str = "") -> str:
    return (request.form.get(name) or default).strip()


def _serialize_assets_for_settings() -> list[dict]:
    result = asset_service.list_assets_service(
        filters={},
        sort=[("asset_tag", "asc")],
        page=1,
        page_size=50,
        include=[],
        retired_mode="all",
    )

    assets = []
    for row in result["items"]:
        item = dict(row)
        for field_name in (
            "asset_id",
            "category_id",
            "site_id",
            "status_id",
            "variant_id",
        ):
            if item.get(field_name) is not None:
                item[field_name] = str(item[field_name])
        assets.append(item)

    return assets


def _build_asset_form_context(form_values: dict | None = None) -> dict:
    form_values = dict(form_values or {})
    current_site = site_service.get_current_site() or {}

    selected_site_id = (form_values.get("site_id") or current_site.get("id") or "").strip()
    selected_category_id = (form_values.get("category_id") or "").strip()
    selected_make_id = (form_values.get("make_id") or "").strip()
    selected_model_id = (form_values.get("model_id") or "").strip()
    selected_variant_id = (form_values.get("variant_id") or "").strip()
    selected_status_id = (form_values.get("status_id") or "").strip()

    site_options = site_service.list_sites()
    category_options = lookups.list_asset_categories()
    status_options = lookups.list_asset_statuses()

    try:
        make_options = lookups.list_makes(category_id=selected_category_id) if selected_category_id else []
    except ValueError:
        selected_category_id = ""
        selected_make_id = ""
        selected_model_id = ""
        selected_variant_id = ""
        make_options = []
    if selected_make_id and selected_make_id not in {item["id"] for item in make_options}:
        selected_make_id = ""
        selected_model_id = ""
        selected_variant_id = ""

    try:
        model_options = lookups.list_models(make_id=selected_make_id) if selected_make_id else []
    except ValueError:
        selected_make_id = ""
        selected_model_id = ""
        selected_variant_id = ""
        model_options = []
    if selected_model_id and selected_model_id not in {item["id"] for item in model_options}:
        selected_model_id = ""
        selected_variant_id = ""

    try:
        variant_options = lookups.list_variants(model_id=selected_model_id) if selected_model_id else []
    except ValueError:
        selected_model_id = ""
        selected_variant_id = ""
        variant_options = []
    if selected_variant_id and selected_variant_id not in {item["id"] for item in variant_options}:
        selected_variant_id = ""

    form_values.update(
        {
            "site_id": selected_site_id,
            "category_id": selected_category_id,
            "make_id": selected_make_id,
            "model_id": selected_model_id,
            "variant_id": selected_variant_id,
            "status_id": selected_status_id,
            "asset_tag": (form_values.get("asset_tag") or "").strip(),
        }
    )

    return {
        "form_values": form_values,
        "site_options": site_options,
        "category_options": category_options,
        "make_options": make_options,
        "model_options": model_options,
        "variant_options": variant_options,
        "status_options": status_options,
        "assets": _serialize_assets_for_settings(),
        "site_by_id": {site["id"]: site for site in site_options},
        "category_by_id": {category["id"]: category for category in category_options},
        "status_by_id": {status["id"]: status for status in status_options},
    }


@web_bp.get("/settings", strict_slashes=False)
def settings():
    return _render_settings(
        "settings/index.html",
        active_tab="home",
    )


@web_bp.route("/settings/sites", methods=["GET", "POST"], strict_slashes=False)
def settings_sites():
    form_values = {
        "fullname": _clean_form_value("fullname"),
        "shorthand": _clean_form_value("shorthand"),
    }
    form_error = None
    status_code = 200

    if request.method == "POST":
        if not _settings_unlocked():
            form_error = "Unlock settings before adding a site."
            status_code = 403
        else:
            try:
                site_service.create_site(
                    fullname=form_values["fullname"],
                    shorthand=form_values["shorthand"],
                )
            except ValueError as exc:
                form_error = str(exc)
                status_code = 400
            else:
                return redirect(url_for("app.settings_sites", created="1"))

    response = _render_settings(
        "settings/sites.html",
        active_tab="sites",
        sites=site_service.list_sites(),
        form_values=form_values,
        form_error=form_error,
        created=request.args.get("created") == "1",
    )
    return response, status_code


@web_bp.route("/settings/categories", methods=["GET", "POST"], strict_slashes=False)
def settings_categories():
    form_values = {
        "name": _clean_form_value("name"),
    }
    form_error = None
    status_code = 200

    if request.method == "POST":
        if not _settings_unlocked():
            form_error = "Unlock settings before adding a category."
            status_code = 403
        else:
            try:
                lookups.create_category(name=form_values["name"])
            except ValueError as exc:
                form_error = str(exc)
                status_code = 400
            else:
                return redirect(url_for("app.settings_categories", created="1"))

    response = _render_settings(
        "settings/categories.html",
        active_tab="categories",
        categories=lookups.list_categories(),
        form_values=form_values,
        form_error=form_error,
        created=request.args.get("created") == "1",
    )
    return response, status_code


@web_bp.route("/settings/makes", methods=["GET", "POST"], strict_slashes=False)
def settings_makes():
    form_values = {
        "category_id": _clean_form_value("category_id"),
        "name": _clean_form_value("name"),
    }
    form_error = None
    status_code = 200

    if request.method == "POST":
        if not _settings_unlocked():
            form_error = "Unlock settings before adding a make."
            status_code = 403
        else:
            try:
                lookups.create_make(
                    category_id=form_values["category_id"],
                    name=form_values["name"],
                )
            except ValueError as exc:
                form_error = str(exc)
                status_code = 400
            else:
                return redirect(url_for("app.settings_makes", created="1"))

    response = _render_settings(
        "settings/makes.html",
        active_tab="makes",
        makes=lookups.list_makes(),
        categories=lookups.list_categories(),
        form_values=form_values,
        form_error=form_error,
        created=request.args.get("created") == "1",
    )
    return response, status_code


@web_bp.route("/settings/models", methods=["GET", "POST"], strict_slashes=False)
def settings_models():
    form_values = {
        "make_id": _clean_form_value("make_id"),
        "name": _clean_form_value("name"),
    }
    form_error = None
    status_code = 200

    if request.method == "POST":
        if not _settings_unlocked():
            form_error = "Unlock settings before adding a model."
            status_code = 403
        else:
            try:
                lookups.create_model(
                    make_id=form_values["make_id"],
                    name=form_values["name"],
                )
            except ValueError as exc:
                form_error = str(exc)
                status_code = 400
            else:
                return redirect(url_for("app.settings_models", created="1"))

    response = _render_settings(
        "settings/models.html",
        active_tab="models",
        models=lookups.list_models(),
        makes=lookups.list_makes(),
        form_values=form_values,
        form_error=form_error,
        created=request.args.get("created") == "1",
    )
    return response, status_code


@web_bp.route("/settings/variants", methods=["GET", "POST"], strict_slashes=False)
def settings_variants():
    form_values = {
        "model_id": _clean_form_value("model_id"),
        "name": _clean_form_value("name"),
    }
    form_error = None
    status_code = 200

    if request.method == "POST":
        if not _settings_unlocked():
            form_error = "Unlock settings before adding a variant."
            status_code = 403
        else:
            try:
                lookups.create_variant(
                    model_id=form_values["model_id"],
                    name=form_values["name"],
                )
            except ValueError as exc:
                form_error = str(exc)
                status_code = 400
            else:
                return redirect(url_for("app.settings_variants", created="1"))

    response = _render_settings(
        "settings/variants.html",
        active_tab="variants",
        variants=lookups.list_variants(),
        models=lookups.list_models(),
        form_values=form_values,
        form_error=form_error,
        created=request.args.get("created") == "1",
    )
    return response, status_code


@web_bp.route("/settings/assets/new", methods=["GET", "POST"], strict_slashes=False)
def settings_new_asset():
    form_values = {
        "asset_tag": _clean_form_value("asset_tag"),
        "site_id": _clean_form_value("site_id"),
        "category_id": _clean_form_value("category_id"),
        "make_id": _clean_form_value("make_id"),
        "model_id": _clean_form_value("model_id"),
        "variant_id": _clean_form_value("variant_id"),
        "status_id": _clean_form_value("status_id"),
    }
    form_error = None
    status_code = 200

    if request.method == "POST":
        if not _settings_unlocked():
            form_error = "Unlock settings before adding an asset."
            status_code = 403
        else:
            try:
                created_asset = asset_service.create_asset_service(form_values)
            except ValueError as exc:
                form_error = str(exc)
                status_code = 400
            else:
                return redirect(
                    url_for(
                        "app.settings_new_asset",
                        created="1",
                        asset_id=str(created_asset["id"]),
                    )
                )

    created_asset = None
    created_asset_id = (request.args.get("asset_id") or "").strip()
    if request.args.get("created") == "1" and created_asset_id:
        try:
            UUID(created_asset_id)
        except ValueError:
            created_asset = None
        else:
            created_asset = asset_service.get_asset_service(created_asset_id)

    response = _render_settings(
        "settings/assets_new.html",
        active_tab="assets",
        form_error=form_error,
        created=request.args.get("created") == "1",
        created_asset=created_asset,
        **_build_asset_form_context(form_values),
    )
    return response, status_code
