from flask import request, jsonify, abort
from . import bp
from app.services import issues as issue_service
from uuid import UUID

def parse_uuid_arg(name: str):
    v = request.args.get(name)
    if not v:
        return None
    try:
        UUID(v)
    except ValueError:
        abort(400, f"Invalid {name}, must be UUID")
    return v

def parse_uuid_field(data: dict, name: str, required: bool = False):
    """
    Parse a UUID from a JSON body field.
    - If required and missing/empty -> 400
    - If present but invalid -> 400
    - If optional and missing -> None
    """
    v = data.get(name)
    if v is None or v == "":
        if required:
            abort(400, description=f"Missing required field: {name}")
        return None

    try:
        UUID(v)
    except ValueError:
        abort(400, description=f"Invalid {name}, must be UUID")

    return v

def validate_uuid_path(value: str, field_name: str = "id"):
    """
    Validate a UUID coming from the URL path.
    """
    try:
        UUID(value)
    except ValueError:
        abort(400, description=f"Invalid {field_name}, must be UUID")
    return value

@bp.route("/issues", methods=["GET"])
def list_issues():
    page = request.args.get("page", default=1, type=int)
    page_size = request.args.get("page_size", default=50, type=int)

    filters = {
        "site_id": parse_uuid_arg("site_id"),
        "asset_id": parse_uuid_arg("asset_id"),
        "status_id": parse_uuid_arg("status_id"),
        # reported_by is now a plain optional string
        "reported_by": request.args.get("reported_by"),
        "created_from": request.args.get("created_from"),
        "created_to": request.args.get("created_to"),
        "closed": request.args.get("closed"),
        "search": request.args.get("search"),
    }

    result = issue_service.list_issues(page, page_size, filters)
    return jsonify(result)

@bp.route("/issues/<issue_id>", methods=["GET"])
def get_issue(issue_id):
    # Validate UUID format
    try:
        UUID(issue_id)
    except ValueError:
        abort(400, description="Invalid issue_id, must be UUID")

    issue = issue_service.get_issue(issue_id)
    if issue is None:
        abort(404, description="Issue not found")

    return jsonify(issue)

@bp.route("/issues", methods=["POST"])
def create_issue():
    data = request.get_json(silent=True) or {}

    asset_id = parse_uuid_field(data, "asset_id", required=True)
    reported_by = data.get("reported_by")
    created_by = data.get("created_by")
    status_id = parse_uuid_field(data, "status_id", required=False)

    title = data.get("title")
    description = data.get("description")

    if not asset_id or not title or not description:
        abort(400, description="Missing required fields: asset_id, created_by, title, description")

    payload = {
        "asset_id": asset_id,
        "reported_by": reported_by,
        "created_by": created_by,
        "status_id": status_id,
        "title": title,
        "description": description,
        "initial_action_body": data.get("initial_action_body"),
    }

    try:
        result = issue_service.create_issue(payload)
    except ValueError as e:
        abort(400, description=str(e))

    return jsonify(result), 201

@bp.route("/issues/<issue_id>/actions", methods=["POST"])
def create_issue_action(issue_id):
    validate_uuid_path(issue_id, "issue_id")

    data = request.get_json(silent=True) or {}

    # optional string
    created_by = data.get("created_by")  # may be None, service will default "-"

    # optional status change
    new_status_id = parse_uuid_field(data, "new_status_id", required=False)

    action_type_code = data.get("action_type_code")
    body = data.get("body")

    if not action_type_code or not body:
        abort(400, description="Missing required fields: action_type_code, body")

    payload = {
        "action_type_code": action_type_code,
        "body": body,
        "created_by": created_by,
        "new_status_id": new_status_id,
    }

    try:
        result = issue_service.add_issue_action(issue_id, payload)
    except ValueError as e:
        abort(400, description=str(e))

    if result is None:
        abort(404, description="Issue not found")

    return jsonify(result), 201