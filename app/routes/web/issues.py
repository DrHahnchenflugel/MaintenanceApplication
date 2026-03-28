from uuid import UUID

from flask import abort, redirect, render_template, request, url_for

from . import bp
from app.services import assets as asset_service
from app.services import issues as issue_service
from app.services import lookups
from app.services import sites as site_service


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


def _new_issue_form_values(asset_id: str | None, asset: dict | None):
    return {
        "asset_id": (request.form.get("asset_id") or asset_id or "").strip(),
        "asset_status_id": (
            (request.form.get("asset_status_id") or ((asset or {}).get("status_id")) or "")
        ).strip(),
        "title": request.form.get("title") or "",
        "description": request.form.get("description") or "",
        "reported_by": request.form.get("reported_by") or "",
    }


def _issue_action_form_values():
    return {
        "action_type_code": ((request.form.get("action_type_code") or "").strip().upper()),
        "new_status_id": (request.form.get("new_status_id") or "").strip(),
        "new_asset_status_id": (request.form.get("new_asset_status_id") or "").strip(),
        "created_by": request.form.get("created_by") or "",
        "body": request.form.get("body") or "",
    }


def _render_new_issue_form(*, asset: dict | None, asset_id: str | None, form_error: str | None):
    return render_template(
        "issues/new_issue.html",
        asset=asset,
        asset_id=asset_id,
        asset_status_options=asset_service.list_asset_statuses(),
        category_options=lookups.list_asset_categories(),
        make_options=lookups.list_makes(),
        form_values=_new_issue_form_values(asset_id, asset),
        form_error=form_error,
    )


def _render_issue_detail(*, issue: dict, form_error: str | None):
    return render_template(
        "issues/specific_issue.html",
        issue=issue,
        status_options=issue_service.list_issue_statuses(),
        action_types=issue_service.list_action_types(),
        asset_status_options=asset_service.list_asset_statuses(),
        form_values=_issue_action_form_values(),
        form_error=form_error,
    )


@bp.route("/issues")
@bp.route("/issues/")
def issues_list():
    """
    Server-rendered issues list page.
    Query params:
      - status: optional status code (OPEN, IN_PROGRESS, BLOCKED, CLOSED)
      - q:      optional search text (title/description)
    """

    site_filter_was_explicit, requested_site_id = parse_site_filter_arg("site_id")
    current_site = site_service.get_current_site()
    site_id = requested_site_id if site_filter_was_explicit else ((current_site or {}).get("id"))

    raw_category = request.args.get("category_id", None)
    category_id = parse_uuid_arg("category_id")
    categories = lookups.list_categories()

    if raw_category is None:
        robot = next(
            (
                category
                for category in categories
                if (category.get("label") or "").strip().lower() == "robot"
                or (category.get("name") or "").strip().lower() == "robot"
            ),
            None,
        )
        if robot:
            category_id = robot["id"]

    make_id = parse_uuid_arg("make_id")
    model_id = parse_uuid_arg("model_id")
    variant_id = parse_uuid_arg("variant_id")

    if not category_id:
        make_id = None
        model_id = None
        variant_id = None
    elif not make_id:
        model_id = None
        variant_id = None
    elif not model_id:
        variant_id = None

    makes = lookups.list_makes(category_id=category_id) if category_id else []
    models = lookups.list_models(make_id=make_id) if make_id else []
    variants = lookups.list_variants(model_id=model_id) if model_id else []

    if make_id and make_id not in {item["id"] for item in makes}:
        make_id = None
        model_id = None
        variant_id = None
        models = []
        variants = []

    if model_id and model_id not in {item["id"] for item in models}:
        model_id = None
        variant_id = None
        variants = []

    if variant_id and variant_id not in {item["id"] for item in variants}:
        variant_id = None

    raw_status = request.args.get("status", None)
    status_code = (request.args.get("status") or "").strip().upper() or None

    if raw_status is None:
        status_code = "IN_PROGRESS"

    search = request.args.get("q") or None

    status_options = issue_service.list_issue_statuses()
    status_by_code = {status["code"]: status for status in status_options}

    filters = {
        "site_id": site_id,
        "asset_id": None,
        "status_id": None,
        "reported_by": None,
        "created_from": None,
        "created_to": None,
        "search": search,
        "category_id": category_id,
        "make_id": make_id,
        "model_id": model_id,
        "variant_id": variant_id,
        "active_status_ids": None,
    }

    if status_code and status_code in status_by_code:
        filters["status_id"] = status_by_code[status_code]["id"]
    elif status_code == "ACTIVE":
        filters["status_id"] = "00000000-0000-0000-0000-000000000000"
        filters["active_status_ids"] = (
            status_by_code["OPEN"]["id"],
            status_by_code["IN_PROGRESS"]["id"],
        )

    result = issue_service.list_issues(page=1, page_size=200, filters=filters)

    return render_template(
        "issues/list_issues.html",
        issues=result["items"],
        status_options=status_options,
        cur_site_id=site_id,
        cur_status=status_code,
        search=search or "",
        categories=categories,
        makes=makes,
        models=models,
        variants=variants,
        cur_category_id=category_id,
        cur_make_id=make_id,
        cur_model_id=model_id,
        cur_variant_id=variant_id,
        category_options=lookups.list_asset_categories(),
        make_options=lookups.list_makes(),
    )


@bp.route("/issues/<issue_id>")
@bp.route("/issues/<issue_id>/")
def view_issue(issue_id):
    issue = issue_service.get_issue(issue_id)
    if issue is None:
        abort(404)

    return _render_issue_detail(issue=issue, form_error=None)


@bp.route("/issues/<issue_id>/add-action", methods=["POST"])
def add_issue_action(issue_id):
    body = (request.form.get("body") or "").strip()
    action_type_code = (request.form.get("action_type_code") or "").strip().upper()
    created_by = (request.form.get("created_by") or "").strip() or None

    new_status_id = (request.form.get("new_status_id") or "").strip()
    if new_status_id:
        try:
            new_status_id = str(UUID(new_status_id))
        except ValueError:
            issue = issue_service.get_issue(issue_id)
            if issue is None:
                abort(404)
            return _render_issue_detail(issue=issue, form_error="New status must be a valid UUID."), 400
    else:
        new_status_id = None

    new_asset_status_id = (request.form.get("new_asset_status_id") or "").strip()
    if new_asset_status_id:
        try:
            new_asset_status_id = str(UUID(new_asset_status_id))
        except ValueError:
            issue = issue_service.get_issue(issue_id)
            if issue is None:
                abort(404)
            return _render_issue_detail(
                issue=issue,
                form_error="Change Asset Status must be a valid UUID.",
            ), 400
    else:
        new_asset_status_id = None

    try:
        result = issue_service.add_issue_action(
            issue_id,
            {
                "action_type_code": action_type_code,
                "body": body,
                "created_by": created_by,
                "new_status_id": new_status_id,
                "new_asset_status_id": new_asset_status_id,
            },
        )
    except ValueError as exc:
        issue = issue_service.get_issue(issue_id)
        if issue is None:
            abort(404)
        return _render_issue_detail(issue=issue, form_error=str(exc)), 400

    if result is None:
        abort(404)

    return redirect(url_for("app.view_issue", issue_id=issue_id))


@bp.route("/issues/new")
@bp.route("/issues/new/")
def new_issue_form():
    asset_id = parse_uuid_arg("asset_id")
    asset = asset_service.get_asset(asset_id) if asset_id else None
    if asset_id and asset is None:
        abort(404, description="Asset not found")

    return _render_new_issue_form(asset=asset, asset_id=asset_id, form_error=None)


@bp.route("/issues", methods=["POST"])
def create_issue_web():
    asset_id = (request.form.get("asset_id") or "").strip()
    asset_status_id = (request.form.get("asset_status_id") or "").strip()
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    photo = request.files.get("photo")
    reported_by = (request.form.get("reported_by") or "").strip()

    if asset_id:
        try:
            asset_id = str(UUID(asset_id))
        except ValueError:
            return _render_new_issue_form(
                asset=None,
                asset_id=None,
                form_error="Asset is invalid. Select an asset from the picker.",
            ), 400

    asset = asset_service.get_asset(asset_id) if asset_id else None

    if not asset_id:
        return _render_new_issue_form(
            asset=asset,
            asset_id=asset_id,
            form_error="Asset is required. Scan the QR or use 'Not your robot?' to select one.",
        ), 400

    if asset is None:
        abort(404, description="Asset not found")

    if not asset_status_id:
        return _render_new_issue_form(
            asset=asset,
            asset_id=asset_id,
            form_error="Asset Status is required.",
        ), 400

    try:
        asset_status_id = str(UUID(asset_status_id))
    except ValueError:
        return _render_new_issue_form(
            asset=asset,
            asset_id=asset_id,
            form_error="Asset Status is invalid.",
        ), 400

    if not title:
        return _render_new_issue_form(
            asset=asset,
            asset_id=asset_id,
            form_error="Issue Title is required.",
        ), 400

    if len(title) > 50:
        return _render_new_issue_form(
            asset=asset,
            asset_id=asset_id,
            form_error="Issue Title must be 50 characters or less.",
        ), 400

    if not description:
        return _render_new_issue_form(
            asset=asset,
            asset_id=asset_id,
            form_error="Issue Description is required.",
        ), 400

    try:
        created = issue_service.create_issue(
            {
                "asset_id": asset_id,
                "asset_status_id": asset_status_id,
                "title": title,
                "description": description,
                "reported_by": reported_by or None,
            }
        )
    except ValueError as exc:
        return _render_new_issue_form(
            asset=asset,
            asset_id=asset_id,
            form_error=str(exc),
        ), 400

    issue_id = created["id"]

    if photo and getattr(photo, "filename", ""):
        try:
            issue_service.add_issue_attachment(issue_id, photo)
        except ValueError as exc:
            return _render_new_issue_form(
                asset=asset_service.get_asset(asset_id),
                asset_id=asset_id,
                form_error=f"Photo upload failed: {str(exc)}",
            ), 400

    return redirect(url_for("app.view_issue", issue_id=issue_id))
