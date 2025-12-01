from flask import jsonify, request
from . import bp

@bp.route("/issues", methods=["GET"])
def list_issues():
    return jsonify({"id": "issues"}), 200
