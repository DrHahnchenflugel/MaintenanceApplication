from flask import render_template, request, redirect, url_for, abort
from . import bp
from app.services import lookups 

from app.services import issues as issue_service
from uuid import UUID

def parse_uuid_arg(name: str):
    v = (request.args.get(name) or "").strip()
    if not v:
        return None
    try:
        UUID(v)
    except ValueError:
        abort(400, description=f"Invalid {name}, must be UUID")
    return v

def parse_uuid_form(name: str):
    v = (request.form.get(name) or "").strip()
    if not v:
        return None
    try:
        UUID(v)
    except ValueError:
        abort(400, description=f"Invalid {name}, must be UUID")
    return v

@bp.route("/issues")
@bp.route("/issues/")
def issues_list():
    """
    Server-rendered issues list page.
    Query params:
      - status: optional status code (OPEN, IN_PROGRESS, BLOCKED, CLOSED)
      - q:      optional search text (title/description)
    """

    raw_category = request.args.get("category_id", None)  # None = not present
    category_id = parse_uuid_arg("category_id")
    categories = issue_service.list_categories()

    if raw_category is None:
        robot = next(
            (c for c in categories
            if (c.get("label") or "").strip().lower() == "robot"
            or (c.get("name") or "").strip().lower() == "robot"),
            None
        )
        if robot:
            category_id = robot["id"]

    make_id     = parse_uuid_arg("make_id")
    model_id    = parse_uuid_arg("model_id")
    variant_id  = parse_uuid_arg("variant_id")

    # Cascading reset
    if not category_id:
        make_id = model_id = variant_id = None
    elif not make_id:
        model_id = variant_id = None
    elif not model_id:
        variant_id = None

    makes      = issue_service.list_makes(category_id) if category_id else []
    models     = issue_service.list_models(make_id) if make_id else []
    variants   = issue_service.list_variants(model_id) if model_id else []

    if make_id and make_id not in {m["id"] for m in makes}:
        make_id = model_id = variant_id = None
        models = []
        variants = []

    if model_id and model_id not in {m["id"] for m in models}:
        model_id = variant_id = None
        variants = []

    if variant_id and variant_id not in {v["id"] for v in variants}:
        variant_id = None

    # Read filters from query string
    raw_status = request.args.get("status", None)  # None = missing
    status_code = (request.args.get("status") or "").strip().upper() or None

    if raw_status is None:
        status_code = "IN_PROGRESS"

    search = request.args.get("q") or None

    # Get all statuses so we can render the dropdown and map codes -> ids
    status_options = issue_service.list_issue_statuses()
    status_by_code = {s["code"]: s for s in status_options}

    # default: open-only unless user asks otherwise
    closed_mode = "open"

    if status_code == "CLOSED":
        closed_mode = "all"   # allow closed_at IS NOT NULL rows through
    elif status_code is None:
        # "All" status should show both open and closed
        closed_mode = "all"

    # Build filters for the service layer
    filters = {
        "site_id": None,
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
        filters["active_status_ids"] = (status_by_code["OPEN"]["id"],status_by_code["IN_PROGRESS"]["id"]) # TODO: Sad face

    # For now: single page, large page_size. You can paginate later.
    result = issue_service.list_issues(page=1, page_size=200, filters=filters)

    return render_template(
        "issues/list_issues.html",
        issues=result["items"],
        status_options=status_options,
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
    """
    Show a single issue with actions + status history.
    """

    issue = issue_service.get_issue(issue_id)
    if issue is None:
        abort(404)

    status_options = issue_service.list_issue_statuses()
    action_types = issue_service.list_action_types()

    return render_template(
        "issues/specific_issue.html",
        issue=issue,
        status_options=status_options,
        action_types=action_types,
        form_error=None,
    )

@bp.route("/issues/<issue_id>/add-action", methods=["POST"])
def add_issue_action(issue_id):
    """
    Handle the "Add update" form on the issue detail page.
    """

    body = (request.form.get("body") or "").strip()
    action_type_code = (request.form.get("action_type_code") or "").strip().upper()
    created_by = request.form.get("created_by") or None
    new_status_id = request.form.get("new_status_id") or None

    data = {
        "action_type_code": action_type_code,
        "body": body,
        "created_by": created_by,
        "new_status_id": new_status_id or None,
    }

    try:
        result = issue_service.add_issue_action(issue_id, data)
    except ValueError as e:
        # Validation error – re-render page with inline error
        issue = issue_service.get_issue(issue_id)
        if issue is None:
            abort(404)

        status_options = issue_service.list_issue_statuses()
        action_types = issue_service.list_action_types()

        return render_template(
            "issues/specific_issue.html",
            issue=issue,
            status_options=status_options,
            action_types=action_types,
            form_error=str(e),
        ), 400

    if result is None:
        # Issue not found in service
        abort(404)

    return redirect(url_for("app.view_issue", issue_id=issue_id))
    asset = issue_service.get_asset_by_tag(asset_tag)
    if asset is None:
        abort(404, description="Asset not found")
    return redirect(url_for("app.new_issue_form", asset_id=asset["id"]))

@bp.route("/issues/new")
@bp.route("/issues/new/")
def new_issue_form():
    asset_id = parse_uuid_arg("asset_id")
    asset = issue_service.get_asset(asset_id) if asset_id else None
    if asset_id and asset is None:
        abort(404, description="Asset not found")

    return render_template("issues/new_issue.html", asset=asset, form_error=None)

@bp.route("/issues", methods=["POST"])
@bp.route("/issues", methods=["POST"])
def create_issue_web():
    print("FORM:", dict(request.form))
    # Read form values
    asset_id = (request.form.get("asset_id") or "").strip()
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    photo = request.files.get("photo")

    # Validate UUID format if present
    if asset_id:
        try:
            UUID(asset_id)
        except ValueError:
            abort(400, description="Invalid asset_id, must be UUID")

    # Always rehydrate asset for re-render so UI doesn't "forget"
    asset = issue_service.get_asset(asset_id) if asset_id else None

    # Validation
    if not asset_id:
        return render_template(
            "issues/new_issue.html",
            asset=asset,
            form_error="Asset is required. Scan the QR or use 'Not your robot?' to select one.",
        ), 400

    if asset is None:
        abort(404, description="Asset not found")

    if not title:
        return render_template(
            "issues/new_issue.html",
            asset=asset,
            form_error="Issue Title is required.",
        ), 400

    if len(title) > 50:
        return render_template(
            "issues/new_issue.html",
            asset=asset,
            form_error="Issue Title must be 50 characters or less.",
        ), 400

    if not description:
        return render_template(
            "issues/new_issue.html",
            asset=asset,
            form_error="Issue Description is required.",
        ), 400

    payload = {
        "asset_id": asset_id,
        "title": title,
        "description": description,
        "reported_by": None,
        "created_by": "-",
    }

    created = issue_service.create_issue(payload)
    issue_id = created["id"]

    # If you later want photo upload, do it here (after issue is created)

    return redirect(url_for("app.view_issue", issue_id=issue_id))

    asset_id = parse_uuid_form("asset_id")
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()

    # validate asset exists
    if not asset_id:
        return render_template("issues/new_issue.html", asset=None,
                               form_error="Asset is required."), 400

    asset = issue_service.get_asset(asset_id)
    if asset is None:
        abort(404, description="Asset not found")

    if not title:
        return render_template("issues/new_issue.html", asset=asset,
                               form_error="Issue Title is required."), 400
    if len(title) > 50:
        return render_template("issues/new_issue.html", asset=asset,
                               form_error="Issue Title must be 50 characters or less."), 400
    if not description:
        return render_template("issues/new_issue.html", asset=asset,
                               form_error="Issue Description is required."), 400

    created = issue_service.create_issue({
        "asset_id": asset_id,
        "title": title,
        "description": description,
        "reported_by": None,
        "created_by": "-",
    })

    return redirect(url_for("app.view_issue", issue_id=created["id"]))
    """
    Handle New Issue form submit (no image for now).
    """
    asset_id = parse_uuid_form("asset_id")
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()

    # asset must exist
    if not asset_id:
        return render_template(
            "issues/new_issue.html",
            asset=None,
            form_error="Asset is required. Scan the QR or use 'Not your robot?' to select one.",
        ), 400

    asset = issue_service.get_asset(asset_id)
    if asset is None:
        abort(404, description="Asset not found")

    # required fields
    if not title:
        return render_template(
            "issues/new_issue.html",
            asset=asset,
            form_error="Issue Title is required.",
        ), 400

    if len(title) > 50:
        return render_template(
            "issues/new_issue.html",
            asset=asset,
            form_error="Issue Title must be 50 characters or less.",
        ), 400

    if not description:
        return render_template(
            "issues/new_issue.html",
            asset=asset,
            form_error="Issue Description is required.",
        ), 400

    payload = {
        "asset_id": asset_id,
        "title": title,
        "description": description,
        "reported_by": None,
        "created_by": "-",   # keep dumb-simple until you wire auth
    }

    try:
        created = issue_service.create_issue(payload)
    except ValueError as e:
        return render_template(
            "issues/new_issue.html",
            asset=asset,
            form_error=str(e),
        ), 400

    return redirect(url_for("app.view_issue", issue_id=created["id"]))
    """
    Handle New Issue form submit (multipart/form-data).
    Creates the issue, then uploads optional photo as attachment.
    """

    asset_id = parse_uuid_form("asset_id")
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()

    # optional file input name="photo"
    photo = request.files.get("photo")

    # Required field validation
    if not asset_id:
        asset = None
        return render_template(
            "issues/new_issue.html",
            asset=asset,
            form_error="Asset is required. If you scanned the wrong QR, use 'Not your robot?'",
        ), 400

    asset = issue_service.get_asset(asset_id)
    if asset is None:
        abort(404, description="Asset not found")

    if not title:
        return render_template(
            "issues/new_issue.html",
            asset=asset,
            form_error="Issue Title is required.",
        ), 400

    if len(title) > 50:
        return render_template(
            "issues/new_issue.html",
            asset=asset,
            form_error="Issue Title must be 50 characters or less.",
        ), 400

    if not description:
        return render_template(
            "issues/new_issue.html",
            asset=asset,
            form_error="Issue Description is required.",
        ), 400

    payload = {
        "asset_id": asset_id,
        "title": title,
        "description": description,
        "reported_by": (request.form.get("reported_by") or None),
        # leave status_id empty to default OPEN in service
    }

    try:
        created = issue_service.create_issue(payload)
    except ValueError as e:
        return render_template(
            "issues/new_issue.html",
            asset=asset,
            form_error=str(e),
        ), 400

    issue_id = created["id"]

    return redirect(url_for("app.view_issue", issue_id=issue_id))
