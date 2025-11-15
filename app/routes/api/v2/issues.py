from flask import request, jsonify
from . import api_v2_bp as v2_bp

@v2_bp.route("/issues", methods=[GET])
def listIssues():
    return jsonify({
        "id":"issues"
    })
