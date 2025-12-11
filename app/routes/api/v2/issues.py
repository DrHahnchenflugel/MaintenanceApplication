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

@bp.route("/issues", methods=["GET"])
def list_issues():
    page = request.args.get("page", default=1, type=int)
    page_size = request.args.get("page_size", default=50, type=int)

    filters = {
        "site_id": parse_uuid_arg("site_id"),
        "asset_id": parse_uuid_arg("asset_id"),
        "status_id": parse_uuid_arg("status_id"),
        "reported_by": parse_uuid_arg("reported_by"),
        "created_from": request.args.get("created_from"),
        "created_to": request.args.get("created_to"),
        "closed": request.args.get("closed"),
        "search": request.args.get("search"),
    }

    result = issue_service.list_issues(page, page_size, filters)
    return jsonify(result)
