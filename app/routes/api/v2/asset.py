from flask import request, jsonify
from . import api_v2_bp as v2_bp

@v2_bp.route("/assets", methods=[GET])
def listAssets():
    return jsonify({
        "value": "assets"
    })