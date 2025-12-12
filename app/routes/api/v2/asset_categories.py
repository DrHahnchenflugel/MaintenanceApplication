from flask import jsonify
from . import bp
from app.services import lookups

@bp.get("/asset-categories")
def list_asset_categories():
    return jsonify(lookups.list_asset_categories())
