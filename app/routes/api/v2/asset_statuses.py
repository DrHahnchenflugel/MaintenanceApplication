from flask import jsonify
from . import bp
from app.services import assets as asset_service

@bp.get("/asset-statuses")
def list_asset_statuses():
    return jsonify({"items": asset_service.list_asset_statuses()})
