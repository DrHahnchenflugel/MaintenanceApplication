from flask import request, jsonify
from . import bp
from app.services import assets as asset_service

@bp.route("/assets/<int:asset_id>", methods=["GET"])
def get_asset(asset_id):
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
        "site_id": request.args.get("site_id", type=int),
        "category_id": request.args.get("category_id", type=int),
        "status_id": request.args.get("status_id", type=int),
        "make_id": request.args.get("make_id", type=int),
        "model_id": request.args.get("model_id", type=int),
        "variant_id": request.args.get("variant_id", type=int),
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