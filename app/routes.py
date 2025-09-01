from flask import Blueprint, jsonify, abort, render_template, request, redirect, url_for, flash
from .db import query_one, query_all, execute_returning_one, execute
from uuid import UUID

bp = Blueprint("app", __name__)

def _normalise_issue(s: str) -> str:
    return " ".join((s or "").lower().split())

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
    print('|',uuid_str,'|')
    try:
        u = UUID(uuid_str)
    except ValueError as e:
        print(e)
        print("NOT A UUID")
        abort(404) # TODO: cleaner handling

    asset = query_one(
        "select asset_id, uuid, friendly_tag, status from asset where uuid=%s", (uuid_str,)
    )

    if asset == None:
        print("NOT AN ASSET")
        abort(404) #TODO: Cleaner handling?

    asset_id = asset[0]
    open_work_orders = query_all(
        "select work_order_id, status, raw_issue_description, created_at from work_order where asset_id=%s and status <> 'CLOSED'",
        (asset_id,)
    )
    closed_work_orders = query_all(
        "select work_order_id, status, raw_issue_description, created_at from work_order where asset_id=%s and status = 'CLOSED'",
        (asset_id,)
    )
    return render_template("asset.html",
                           asset=asset,
                           open_work_orders=open_work_orders,
                           closed_work_orders=closed_work_orders)

@bp.post("/a/<uuid_str>/issue")
def asset_page(asset_uuid:UUID):
    asset = query_one("select asset_id from asset where uuid=%s", (asset_uuid,))
    if asset == None:
        abort(404)
    asset_id = asset[0]

    issue = (request.form.get("issue") or "").strip()
    if not issue:
        flash("Issue is required")
        return redirect(url_for("app.asset_page", asset_uuid=asset_uuid))

    # Check for recent issues, see if similar issues exist to avoid duplicates
    recent = query_one(
        "select work_order_id, issue from work_order where asset_id = %s and status <> 'CLOSED' "
        +"and created_at >= now() - interval '2 hours'"
        +"order by created_at desc limit 1",
        (asset_id,)
    )

    if recent:
        existing_id, recent_issue = recent
        if _normalise_issue(issue) in _normalise_issue (recent_issue):
            execute (
                "insert into work_log (work_order_id, action, result) values (%s,%s,%s)",
                (existing_id, f"REPORT: {issue}", None)
            )
            flash(f"Similar ticket exists; appended your report to WO-{existing_id}.")
            return redirect(url_for("app.asset_page", asset_uuid=asset_uuid))

    work_order_id = execute_returning_one(
        "insert into work_order (asset_id, status, issue) values (%s, 'OPEN', %s) returning work_order_id",
        (asset_id, issue)
    )[0]
    flash(f"Opened Issue - {work_order_id}")
    return redirect(url_for("app.asset_page", asset_uuid=asset_uuid))
