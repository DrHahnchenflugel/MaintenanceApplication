from flask import abort, request, jsonify
from . import bp
from app.services import assets as asset_service
from uuid import UUID
from app.services import lookups 

def parse_uuid_arg(name: str):
    value = request.args.get(name)
    if not value:
        return None
    try:
        UUID(value)  # validate format only
    except ValueError:
        abort(400, description=f"Invalid {name}, must be UUID")
    return value

@bp.route("/assets", methods=["GET"])
def list_assets():
    page = request.args.get("page", default=1, type=int)
    page_size = request.args.get("page_size", default=50, type=int)
    retired_param = request.args.get("retired", default="active", type=str).lower()

    filters = {
        "site_id": parse_uuid_arg("site_id"),
        "category_id": parse_uuid_arg("category_id"),
        "status_id": parse_uuid_arg("status_id"),
        "make_id": parse_uuid_arg("make_id"),
        "model_id": parse_uuid_arg("model_id"),
        "variant_id": parse_uuid_arg("variant_id"),
        "asset_tag": request.args.get("asset_tag"),  # string
    }

    # retired mode: active (default), retired, all
    if retired_param not in ("", "active", "retired", "all"):
        return jsonify({
            "error": "invalid_retired_param",
            "message": "retired must be one of: active, retired, all"
        }), 400

    if retired_param in ("", "active"):
        retired_mode = "active"
    elif retired_param == "retired":
        retired_mode = "retired"
    else:  # "all"
        retired_mode = "all"

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
        retired_mode=retired_mode,
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

@bp.route("/assets/<uuid:asset_id>", methods=["GET"])
def get_asset(asset_id:UUID):
    include_param = request.args.get("include", "")
    include = [x.strip() for x in include_param.split(",") if x.strip()]

    asset = asset_service.get_asset_service(asset_id, include=include)

    if asset is None:
        return jsonify({"error": "asset_not_found"}), 404

    return jsonify(asset), 200

@bp.route("/assets/<uuid:asset_id>", methods=["PATCH"])
def update_asset(asset_id: UUID):
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "invalid_json", "message": "Request body must be JSON"}), 400

    try:
        asset = asset_service.patch_asset_service(asset_id, data)
    except ValueError as e:
        return jsonify({"error": "invalid_input", "message": str(e)}), 400

    if asset is None:
        # asset_id not found
        return jsonify({"error": "asset_not_found"}), 404

    return jsonify(asset), 200

@bp.route("/assets/<uuid:asset_id>", methods=["DELETE"])
def retire_asset(asset_id: UUID):
    """
    Retire an asset. retire_reason is REQUIRED.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "error": "invalid_json",
            "message": "Request body must be a JSON object"
        }), 400

    retire_reason = data.get("retire_reason")

    # enforce mandatory reason
    if not retire_reason or not isinstance(retire_reason, str) or retire_reason.strip() == "":
        return jsonify({
            "error": "missing_retire_reason",
            "message": "retire_reason is required and must be a non-empty string"
        }), 400

    success = asset_service.retire_asset_service(
        asset_id, retire_reason=retire_reason
    )

    if not success:
        return jsonify({"error": "asset_not_found"}), 404

    return "", 204

@bp.route("/assets/by-tag/<asset_tag>", methods=["GET"])
def get_asset_by_tag(asset_tag: str):
    result = asset_service.list_assets_service(
        filters={"asset_tag": asset_tag},
        sort=[],
        page=1,
        page_size=1,
        include=[],
        retired_mode="all",
    )
    items = result["items"]
    if not items:
        return jsonify({"error": "asset_not_found"}), 404
    return jsonify(items[0]), 200

@bp.route("/assets/makes", methods=["GET"])
def list_makes_for_assets():
    """
    List makes, optionally filtered by category_id.
    Example:
      /maintenance/api/v2/assets/makes?category_id=<uuid>
    """
    category_id = parse_uuid_arg("category_id")

    items = lookups.list_makes(category_id=category_id)
    return jsonify(items), 200

@bp.route("/assets/models", methods=["GET"])
def list_models_for_assets():
    make_id = parse_uuid_arg("make_id")
    if not make_id:
        return jsonify({"error": "missing_make_id"}), 400

    items = lookups.list_models(make_id=make_id)
    return jsonify(items), 200

@bp.route("/assets/variants", methods=["GET"])
def list_variants_for_assets():
    model_id = parse_uuid_arg("model_id")
    if not model_id:
        return jsonify({"error": "missing_model_id"}), 400

    items = lookups.list_variants(model_id=model_id)
    return jsonify(items), 200