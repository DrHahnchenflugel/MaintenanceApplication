from flask import jsonify
from . import bp
from app.services import lookups

@bp.get("/asset-statuses")
def list_asset_statuses():
    return jsonify(lookups.list_asset_statuses())
