import os
from flask import request, jsonify, abort, send_file, current_app
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

def parse_uuid_path(value: str, name: str):
    try:
        UUID(value)
        return(value)
    except ValueError:
        abort(400, description=f"Invalid {name}, must be UUID")

@bp.route("/issues", methods=["GET"])
def list_issues():
    page = request.args.get("page", default=1, type=int)
    page_size = request.args.get("page_size", default=50, type=int)

    filters = {
        "site_id": parse_uuid_arg("site_id"),
        "asset_id": parse_uuid_arg("asset_id"),
        "status_id": parse_uuid_arg("status_id"),
        "reported_by": request.args.get("reported_by"),
        "created_from": request.args.get("created_from"),
        "created_to": request.args.get("created_to"),
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

@bp.route("/issues/<issue_id>/attachment", methods=["GET"])
def get_issue_attachment(issue_id):
    issue_id = parse_uuid_path(issue_id, "issue_id")

    row = issue_service.get_issue_attachment(issue_id)
    if not row:
        abort(404, description="No attachment for this issue")

    rel = row["filepath"]
    rel_norm = rel.replace("\\", "/")
    if rel_norm.startswith("/") or ".." in rel_norm:
        abort(500, description="Invalid attachment filepath stored")

    attachment_root = current_app.config.get("ATTACHMENT_ROOT", "/tmp/attachments")
    abs_path = os.path.join(attachment_root, rel_norm)

    if not os.path.isfile(abs_path):
        abort(404, description="Attachment file missing on disk")

    return send_file(
        abs_path,
        mimetype=row["content_type"],
        as_attachment=False,
        conditional=True,
    )

@bp.route("/issues/<issue_id>/attachment", methods=["POST"])
def upload_issue_attachment(issue_id):
    issue_id = validate_uuid_path(issue_id, "issue_id")

    f = request.files.get("file")
    try:
        row = issue_service.add_issue_attachment(issue_id, f)
    except ValueError as e:
        abort(400, description=str(e))

    return jsonify(row), 201

@bp.route("/attachment-content-types", methods=["GET"])
def list_attachment_content_types():
    items = issue_service.list_accepted_attachment_content_types()
    return jsonify({"items": items})

@bp.route("/attachment-content-types", methods=["POST"])
def create_attachment_content_type():
    data = request.get_json(silent=True) or {}

    try:
        result = issue_service.create_accepted_attachment_content_type(data)
    except ValueError as e:
        abort(400, description=str(e))
    except Exception:
        # likely unique constraint
        abort(409, description="Duplicate content_type")

    return jsonify(result), 201

@bp.route("/attachment-content-types/<content_type>", methods=["DELETE"])
def delete_attachment_content_type(content_type):
    try:
        issue_service.delete_accepted_attachment_content_type(content_type)
    except ValueError as e:
        abort(404, description=str(e))

    return "", 204

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
        abort(400, description="Missing required fields: asset_id, title, description")

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

@bp.route("/issues/<issue_id>", methods=["PATCH"])
def patch_issue(issue_id):
    validate_uuid_path(issue_id, "issue_id")

    data = request.get_json(silent=True) or {}

    # Optional fields
    title = data.get("title") or None
    description = data.get("description") or None
    reported_by = data.get("reported_by") or None

    asset_id = None
    if "asset_id" in data:
        # If caller sends null, we treat as no change; if non-null, validate UUID
        if data["asset_id"] is not None:
            asset_id = parse_uuid_field(data, "asset_id", required=True)

    payload = {
        "title": title,
        "description": description,
        "reported_by": reported_by,
        "asset_id": asset_id,
    }

    try:
        result = issue_service.update_issue(issue_id, payload)
    except ValueError as e:
        abort(400, description=str(e))

    if result is None:
        abort(404, description="Issue not found")

    return jsonify(result)

@bp.route("/issue-statuses", methods=["GET"])
def get_issue_statuses():
    result = issue_service.list_issue_statuses()
    return jsonify({"items": result})

@bp.route("/action-types", methods=["GET"])
def get_action_types():
    result = issue_service.list_action_types()
    return jsonify({"items": result})

@bp.route("/issue-statuses", methods=["POST"])
def create_issue_status():
    data = request.get_json(silent=True) or {}

    try:
        result = issue_service.create_issue_status(data)
    except ValueError as e:
        msg = str(e)
        if "Duplicate code" in msg:
            return jsonify({"error": msg}), 409
        abort(400, description=msg)

    return jsonify(result), 201

@bp.route("/action-types", methods=["POST"])
def create_action_type():
    data = request.get_json(silent=True) or {}

    try:
        result = issue_service.create_action_type(data)
    except ValueError as e:
        abort(400, description=str(e))

    return jsonify(result), 201
