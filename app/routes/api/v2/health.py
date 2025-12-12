from flask import jsonify
from . import bp

@bp.get("/health")
def health():
    return jsonify({"ok": True})
