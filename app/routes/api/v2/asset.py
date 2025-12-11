from flask import abort, request, jsonify
from . import bp
from app.services import assets as asset_service
from uuid import UUID

def parse_uuid_arg(name: str):
    value = request.args.get(name)
    if not value:
        return None
    try:
        UUID(value)  # validate format only
    except ValueError:
        abort(400, description=f"Invalid {name}, must be UUID")
    return value


@bp.route("/assets/<uuid:asset_id>", methods=["GET"])
def get_asset(asset_id:UUID):
    include_param = request.args.get("include", "")
    include = [x.strip() for x in include_param.split(",") if x.strip()]

    asset = asset_service.get_asset_service(asset_id, include=include)

    if asset is None:
        return jsonify({"error": "asset_not_found"}), 404

    return jsonify(asset), 200


@bp.route("/assets", methods=["GET"])
def list_assets():
    page = request.args.get("page", default=1, type=int)
    page_size = request.args.get("page_size", default=50, type=int)

    filters = {
        "site_id": parse_uuid_arg("site_id"),
        "category_id": parse_uuid_arg("category_id"),
        "status_id": parse_uuid_arg("status_id"),
        "make_id": parse_uuid_arg("make_id"),
        "model_id": parse_uuid_arg("model_id"),
        "variant_id": parse_uuid_arg("variant_id"),
        "asset_tag": request.args.get("asset_tag"),  # string
    }

    # Parse sort string like "asset_tag,-created_at"
    sort_param = request.args.get("sort", "")
    sort = []
    if sort_param:
        for part in sort_param.split(","):
            part = part.strip()
            if not part:
                continue
            direction = "asc"
            field_name = part
            if part.startswith("-"):
                direction = "desc"
                field_name = part[1:]
            sort.append((field_name, direction))

    include_param = request.args.get("include", "")
    include = [x.strip() for x in include_param.split(",") if x.strip()]

    result = asset_service.list_assets_service(
        filters=filters,
        sort=sort,
        page=page,
        page_size=page_size,
        include=include,
    )

    return jsonify(result), 200

@bp.route("/assets", methods=["POST"])
def create_asset():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "invalid_json", "message": "Request body must be JSON"}), 400

    try:
        asset = asset_service.create_asset_service(data)
    except ValueError as e:
        # Validation error from service layer
        return jsonify({"error": "invalid_input", "message": str(e)}), 400

    # TODO: add return location header
    return jsonify(asset), 201