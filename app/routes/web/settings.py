from flask import abort, redirect, render_template, request, url_for
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


def _clean_intent(default: str = "create") -> str:
    return (_clean_form_value("intent", default) or default).lower()


def _normalize_uuid_text(value, field_name: str, *, required: bool = False) -> str | None:
    raw_value = (value or "").strip()
    if not raw_value:
        if required:
            raise ValueError(f"Missing required field: {field_name}")
        return None

    try:
        return str(UUID(raw_value))
    except ValueError:
        raise ValueError(f"Invalid {field_name}, must be a UUID string")


def _get_edit_id_arg() -> str | None:
    raw_value = (request.args.get("edit_id") or "").strip()
    if not raw_value:
        return None

    try:
        return str(UUID(raw_value))
    except ValueError:
        abort(400, description="Invalid edit_id, must be UUID")


def _query_flag(name: str) -> bool:
    return request.args.get(name) == "1"


def _success_context():
    return {
        "created": _query_flag("created"),
        "updated": _query_flag("updated"),
        "deleted": _query_flag("deleted"),
    }


def _unlock_error(intent: str, noun: str) -> str:
    verb = {
        "create": "adding",
        "update": "updating",
        "delete": "deleting",
    }.get(intent, "changing")
    return f"Unlock settings before {verb} {noun}."


def _safe_lookup_item(getter, item_id: str | None):
    if not item_id:
        return None

    try:
        return getter(item_id)
    except ValueError:
        return None


def _require_item_or_404(getter, item_id: str | None):
    item = _safe_lookup_item(getter, item_id)
    if item_id and item is None:
        abort(404)
    return item


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


def _asset_form_values_from_asset(asset: dict) -> dict:
    variant = lookups.get_variant(asset["variant_id"]) or {}
    return {
        "item_id": asset["asset_id"],
        "asset_tag": asset.get("asset_tag") or "",
        "site_id": asset.get("site_id") or "",
        "category_id": asset.get("category_id") or "",
        "make_id": variant.get("make_id") or "",
        "model_id": variant.get("model_id") or "",
        "variant_id": asset.get("variant_id") or "",
        "status_id": asset.get("status_id") or "",
    }


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
    status_options = asset_service.list_asset_statuses()

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
            "item_id": (form_values.get("item_id") or "").strip(),
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
    edit_id = _get_edit_id_arg()
    editing_site = _require_item_or_404(site_service.get_site, edit_id)

    if request.method == "GET":
        if editing_site:
            form_values = {
                "item_id": editing_site["id"],
                "fullname": editing_site["fullname"],
                "shorthand": editing_site["shorthand"],
            }
        else:
            form_values = {
                "item_id": "",
                "fullname": "",
                "shorthand": "",
            }
    else:
        form_values = {
            "item_id": _clean_form_value("item_id"),
            "fullname": _clean_form_value("fullname"),
            "shorthand": _clean_form_value("shorthand"),
        }

    form_error = None
    status_code = 200

    if request.method == "POST":
        intent = _clean_intent()
        if not _settings_unlocked():
            form_error = _unlock_error(intent, "a site")
            status_code = 403
        else:
            try:
                if intent == "update":
                    site_service.update_site(
                        site_id=form_values["item_id"],
                        fullname=form_values["fullname"],
                        shorthand=form_values["shorthand"],
                    )
                    return redirect(url_for("app.settings_sites", updated="1"))
                if intent == "delete":
                    site_service.delete_site(form_values["item_id"])
                    return redirect(url_for("app.settings_sites", deleted="1"))

                site_service.create_site(
                    fullname=form_values["fullname"],
                    shorthand=form_values["shorthand"],
                )
                return redirect(url_for("app.settings_sites", created="1"))
            except ValueError as exc:
                form_error = str(exc)
                status_code = 400

        editing_site = _safe_lookup_item(site_service.get_site, form_values["item_id"])

    response = _render_settings(
        "settings/sites.html",
        active_tab="sites",
        sites=site_service.list_sites(),
        editing_site=editing_site,
        form_values=form_values,
        form_error=form_error,
        **_success_context(),
    )
    return response, status_code


@web_bp.route("/settings/categories", methods=["GET", "POST"], strict_slashes=False)
def settings_categories():
    edit_id = _get_edit_id_arg()
    editing_category = _require_item_or_404(lookups.get_category, edit_id)

    if request.method == "GET":
        if editing_category:
            form_values = {
                "item_id": editing_category["id"],
                "name": editing_category["label"] or editing_category["name"] or "",
            }
        else:
            form_values = {
                "item_id": "",
                "name": "",
            }
    else:
        form_values = {
            "item_id": _clean_form_value("item_id"),
            "name": _clean_form_value("name"),
        }

    form_error = None
    status_code = 200

    if request.method == "POST":
        intent = _clean_intent()
        if not _settings_unlocked():
            form_error = _unlock_error(intent, "a category")
            status_code = 403
        else:
            try:
                if intent == "update":
                    lookups.update_category(
                        category_id=form_values["item_id"],
                        name=form_values["name"],
                    )
                    return redirect(url_for("app.settings_categories", updated="1"))
                if intent == "delete":
                    lookups.delete_category(form_values["item_id"])
                    return redirect(url_for("app.settings_categories", deleted="1"))

                lookups.create_category(name=form_values["name"])
                return redirect(url_for("app.settings_categories", created="1"))
            except ValueError as exc:
                form_error = str(exc)
                status_code = 400

        editing_category = _safe_lookup_item(lookups.get_category, form_values["item_id"])

    response = _render_settings(
        "settings/categories.html",
        active_tab="categories",
        categories=lookups.list_categories(),
        editing_category=editing_category,
        form_values=form_values,
        form_error=form_error,
        **_success_context(),
    )
    return response, status_code


@web_bp.route("/settings/makes", methods=["GET", "POST"], strict_slashes=False)
def settings_makes():
    edit_id = _get_edit_id_arg()
    editing_make = _require_item_or_404(lookups.get_make, edit_id)

    if request.method == "GET":
        if editing_make:
            form_values = {
                "item_id": editing_make["id"],
                "category_id": editing_make["category_id"],
                "name": editing_make["label"] or editing_make["name"] or "",
            }
        else:
            form_values = {
                "item_id": "",
                "category_id": "",
                "name": "",
            }
    else:
        form_values = {
            "item_id": _clean_form_value("item_id"),
            "category_id": _clean_form_value("category_id"),
            "name": _clean_form_value("name"),
        }

    form_error = None
    status_code = 200

    if request.method == "POST":
        intent = _clean_intent()
        if not _settings_unlocked():
            form_error = _unlock_error(intent, "a make")
            status_code = 403
        else:
            try:
                if intent == "update":
                    lookups.update_make(
                        make_id=form_values["item_id"],
                        category_id=form_values["category_id"],
                        name=form_values["name"],
                    )
                    return redirect(url_for("app.settings_makes", updated="1"))
                if intent == "delete":
                    lookups.delete_make(form_values["item_id"])
                    return redirect(url_for("app.settings_makes", deleted="1"))

                lookups.create_make(
                    category_id=form_values["category_id"],
                    name=form_values["name"],
                )
                return redirect(url_for("app.settings_makes", created="1"))
            except ValueError as exc:
                form_error = str(exc)
                status_code = 400

        editing_make = _safe_lookup_item(lookups.get_make, form_values["item_id"])

    response = _render_settings(
        "settings/makes.html",
        active_tab="makes",
        makes=lookups.list_makes(),
        categories=lookups.list_categories(),
        editing_make=editing_make,
        form_values=form_values,
        form_error=form_error,
        **_success_context(),
    )
    return response, status_code


@web_bp.route("/settings/models", methods=["GET", "POST"], strict_slashes=False)
def settings_models():
    edit_id = _get_edit_id_arg()
    editing_model = _require_item_or_404(lookups.get_model, edit_id)

    if request.method == "GET":
        if editing_model:
            form_values = {
                "item_id": editing_model["id"],
                "make_id": editing_model["make_id"],
                "name": editing_model["label"] or editing_model["name"] or "",
            }
        else:
            form_values = {
                "item_id": "",
                "make_id": "",
                "name": "",
            }
    else:
        form_values = {
            "item_id": _clean_form_value("item_id"),
            "make_id": _clean_form_value("make_id"),
            "name": _clean_form_value("name"),
        }

    form_error = None
    status_code = 200

    if request.method == "POST":
        intent = _clean_intent()
        if not _settings_unlocked():
            form_error = _unlock_error(intent, "a model")
            status_code = 403
        else:
            try:
                if intent == "update":
                    lookups.update_model(
                        model_id=form_values["item_id"],
                        make_id=form_values["make_id"],
                        name=form_values["name"],
                    )
                    return redirect(url_for("app.settings_models", updated="1"))
                if intent == "delete":
                    lookups.delete_model(form_values["item_id"])
                    return redirect(url_for("app.settings_models", deleted="1"))

                lookups.create_model(
                    make_id=form_values["make_id"],
                    name=form_values["name"],
                )
                return redirect(url_for("app.settings_models", created="1"))
            except ValueError as exc:
                form_error = str(exc)
                status_code = 400

        editing_model = _safe_lookup_item(lookups.get_model, form_values["item_id"])

    response = _render_settings(
        "settings/models.html",
        active_tab="models",
        models=lookups.list_models(),
        makes=lookups.list_makes(),
        editing_model=editing_model,
        form_values=form_values,
        form_error=form_error,
        **_success_context(),
    )
    return response, status_code


@web_bp.route("/settings/variants", methods=["GET", "POST"], strict_slashes=False)
def settings_variants():
    edit_id = _get_edit_id_arg()
    editing_variant = _require_item_or_404(lookups.get_variant, edit_id)

    if request.method == "GET":
        if editing_variant:
            form_values = {
                "item_id": editing_variant["id"],
                "model_id": editing_variant["model_id"],
                "name": editing_variant["label"] or editing_variant["name"] or "",
            }
        else:
            form_values = {
                "item_id": "",
                "model_id": "",
                "name": "",
            }
    else:
        form_values = {
            "item_id": _clean_form_value("item_id"),
            "model_id": _clean_form_value("model_id"),
            "name": _clean_form_value("name"),
        }

    form_error = None
    status_code = 200

    if request.method == "POST":
        intent = _clean_intent()
        if not _settings_unlocked():
            form_error = _unlock_error(intent, "a variant")
            status_code = 403
        else:
            try:
                if intent == "update":
                    lookups.update_variant(
                        variant_id=form_values["item_id"],
                        model_id=form_values["model_id"],
                        name=form_values["name"],
                    )
                    return redirect(url_for("app.settings_variants", updated="1"))
                if intent == "delete":
                    lookups.delete_variant(form_values["item_id"])
                    return redirect(url_for("app.settings_variants", deleted="1"))

                lookups.create_variant(
                    model_id=form_values["model_id"],
                    name=form_values["name"],
                )
                return redirect(url_for("app.settings_variants", created="1"))
            except ValueError as exc:
                form_error = str(exc)
                status_code = 400

        editing_variant = _safe_lookup_item(lookups.get_variant, form_values["item_id"])

    response = _render_settings(
        "settings/variants.html",
        active_tab="variants",
        variants=lookups.list_variants(),
        models=lookups.list_models(),
        editing_variant=editing_variant,
        form_values=form_values,
        form_error=form_error,
        **_success_context(),
    )
    return response, status_code


@web_bp.route("/settings/assets/new", methods=["GET", "POST"], strict_slashes=False)
def settings_new_asset():
    edit_id = _get_edit_id_arg()
    editing_asset = _require_item_or_404(asset_service.get_asset_service, edit_id)

    if request.method == "GET":
        form_values = (
            _asset_form_values_from_asset(editing_asset)
            if editing_asset is not None
            else {
                "item_id": "",
                "asset_tag": "",
                "site_id": "",
                "category_id": "",
                "make_id": "",
                "model_id": "",
                "variant_id": "",
                "status_id": "",
            }
        )
    else:
        form_values = {
            "item_id": _clean_form_value("item_id"),
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
        intent = _clean_intent()
        if not _settings_unlocked():
            form_error = _unlock_error(intent, "an asset")
            status_code = 403
        else:
            try:
                if intent == "update":
                    updated_asset = asset_service.update_asset_for_settings_service(
                        form_values["item_id"],
                        form_values,
                    )
                    if updated_asset is None:
                        abort(404)
                    return redirect(
                        url_for(
                            "app.settings_new_asset",
                            updated="1",
                            asset_id=updated_asset["asset_id"],
                        )
                    )
                if intent == "delete":
                    asset_service.delete_asset_service(form_values["item_id"])
                    return redirect(url_for("app.settings_new_asset", deleted="1"))

                created_asset = asset_service.create_asset_service(form_values)
                return redirect(
                    url_for(
                        "app.settings_new_asset",
                        created="1",
                        asset_id=str(created_asset["id"]),
                    )
                )
            except ValueError as exc:
                form_error = str(exc)
                status_code = 400

        editing_asset = _safe_lookup_item(asset_service.get_asset_service, form_values["item_id"])

    saved_asset = None
    saved_asset_id = (request.args.get("asset_id") or "").strip()
    if saved_asset_id:
        try:
            UUID(saved_asset_id)
        except ValueError:
            saved_asset = None
        else:
            saved_asset = asset_service.get_asset_service(saved_asset_id)

    response = _render_settings(
        "settings/assets_new.html",
        active_tab="assets",
        form_error=form_error,
        editing_asset=editing_asset,
        saved_asset=saved_asset,
        **_success_context(),
        **_build_asset_form_context(form_values),
    )
    return response, status_code
