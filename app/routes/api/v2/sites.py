from flask import jsonify
from uuid import UUID
from . import bp
from app.services import sites as site_service

@bp.get("/sites")
def list_sites():
    return jsonify(site_service.list_sites())

@bp.get("/sites/<site_id>")
def get_site(site_id):
    # validate UUID format (same pattern you use elsewhere)
    try:
        UUID(site_id)
    except ValueError:
        abort(400, description="Invalid site_id")

    row = site_service.get_site(site_id)
    if row is None:
        abort(404, description="Site not found")

    return jsonify(row)