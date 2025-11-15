from flask import Blueprint, jsonify
from .v2 import bp as api_v2_bp

api_v2_bp = Blueprint("api", __name__)

@api_v2_bp.route("/", methods=["GET"])
def v2_root():
    return jsonify({
        "name":"Exceed Maintenance API",
        "versions":{
            "v2":"/api/v2"
        },
        "resources":{
            "assets":"/assets",
            "issues":"/issues",
            "sites":"/sites",
            "asset_categories":"/categories",
            "asset_statuses":"/asset-statuses",
            "issue_statuses":"/issue-statuses",
            "action_types":"/action-types",
            "health":"/health"
        }
    })