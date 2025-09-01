from flask import Blueprint, jsonify
from .db import query_one

bp = Blueprint("app", __name__)

@bp.get("/ping")
def ping():
    return jsonify(ok = True, pong = "🏓🏓🏓")

@bp.get("/db/ping")
def db_ping():
    version = query_one("select version()")[0]
    site_count = query_one("select count(*) from site")[0]

    return jsonify(ok=True, postgres=version, site_count=site_count)