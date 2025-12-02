from flask import Blueprint, jsonify

# This is the v2 API blueprint
bp = Blueprint("api_v2", __name__, url_prefix="/maintenance/api/v2")
# or "/api/v2" if that’s what you want

# Import modules so they register routes on this blueprint
from . import asset, issues  # noqa: F401

@bp.route("/", methods=["GET"])
def api_v2_root():
    return jsonify({
        "name": "Exceed Maintenance API",
        "version": "2",
        "resources": {
            "health": "/health",
            "assets": "/assets",
            "issues": "/issues",
            "sites": "/sites",
            "action_types": "/action-types",
            "issue_statuses": "/issue-statuses",
            "asset_statuses": "/asset-statuses",
            "asset_categories": "/asset-categories",
        },
    })