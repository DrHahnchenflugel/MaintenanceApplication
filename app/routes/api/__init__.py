from flask import Blueprint, jsonify

# Root API blueprint, just for the `/maintenance/api/` index
bp = Blueprint("api_root", __name__, url_prefix="/maintenance/api")

@bp.route("/", methods=["GET"])
def api_root():
    return jsonify({
        "name": "Exceed Maintenance API",
        "versions": {
            "v2": "/maintenance/api/v2"
        }
    })
