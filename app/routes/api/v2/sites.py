from flask import jsonify
from . import bp
from app.services import sites as site_service

@bp.get("/sites")
def list_sites():
    return jsonify(site_service.list_sites())
