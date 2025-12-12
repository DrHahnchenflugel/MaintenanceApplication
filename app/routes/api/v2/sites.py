from flask import request, jsonify
from . import bp
from app.services import sites as site_service

@bp.get("/sites")
def list_sites():
    page = request.args.get("page", default=1, type=int)
    page_size = request.args.get("page_size", default=50, type=int)

    rows = site_service.list_sites(page=page, page_size=page_size)
    return jsonify(rows)
