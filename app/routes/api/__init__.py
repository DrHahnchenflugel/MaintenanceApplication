from flask import Blueprint, jsonify

# Root API blueprint, just for the `/maintenance/api/` index
bp = Blueprint("api_root", __name__, url_prefix="/maintenance/api")

@bp.route("/", methods=["GET"])
def api_root():
    return jsonify({
        "name": "Exceed Maintenance API",
        "versions": {
            "v2": "/maintenance/api/v2"
        },
        "resources": {
            "assets": "/maintenance/api/v2/assets",
            "issues": "/maintenance/api/v2/issues",
            "sites": "/maintenance/api/v2/sites",
            "asset_categories": "/maintenance/api/v2/categories",
            "asset_statuses": "/maintenance/api/v2/asset-statuses",
            "issue_statuses": "/maintenance/api/v2/issue-statuses",
            "action_types": "/maintenance/api/v2/action-types",
            "health": "/maintenance/api/v2/health",
        }
    })
