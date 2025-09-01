from flask import Blueprint, jsonify, abort, render_template
from .db import query_one, query_all
from uuid import UUID

bp = Blueprint("app", __name__)

@bp.get("/ping")
def ping():
    return jsonify(ok = True, pong = "🏓🏓🏓")

@bp.get("/db/ping")
def db_ping():
    version = query_one("select version()")
    version = version[0] if version else None #safe from 0

    site_count = query_one("select count(*) from site")
    site_count = site_count[0] if site_count else None

    return jsonify(ok=True, postgres=version, site_count=site_count)

@bp.get("/a/<uuid_str>")
def asset_page(uuid_str):
    # validate & normalise uuid
    try:
        u = UUID(uuid_str)
    except ValueError:
        abort(404) # TODO: cleaner handling

    asset = query_one(
        "select asset_id, uuid, friendly_tag, status from asset where uuid=%s", (uuid_str,)
    )

    if asset == None:
        abort(404) #TODO: Cleaner handling?

    asset_id = asset[0]
    open_work_orders = query_all(
        "select work_order_id, status, issue, created_at from work_order where asset_id=%s and status <> 'CLOSED",
        (asset_id,)
    )
    closed_work_orders = query_all(
        "select work_order_id, status, issue, created_at from work_order where asset_id=%s and status = 'CLOSED",
        (asset_id,)
    )
    return render_template("asset.html",
                           asset=asset,
                           open_work_orders=open_work_orders,
                           closed_work_orders=closed_work_orders)