from flask import render_template, request, redirect, url_for, abort
from . import bp  # this is your "app" blueprint (Blueprint("app", ...))

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
    }

    if status_code and status_code in status_by_code:
        filters["status_id"] = status_by_code[status_code]["id"]

    # For now: single page, large page_size. You can paginate later.
    result = issue_service.list_issues(page=1, page_size=200, filters=filters)

    return render_template(
        "issues/list.html",
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
