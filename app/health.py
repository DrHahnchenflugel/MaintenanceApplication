from flask import Blueprint, Response

health_bp = Blueprint("health", __name__)

@health_bp.route("/health", methods=["GET"], strict_slashes=False)
def health():
    return Response("ok", mimetype="text/plain")
