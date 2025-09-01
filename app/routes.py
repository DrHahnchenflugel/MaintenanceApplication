import os, hashlib, time
from flask import Blueprint, jsonify, abort, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from .db import query_one, query_all, execute_returning_one, execute
from uuid import UUID
from werkzeug.utils import secure_filename

bp = Blueprint("app", __name__)

def _normalise_issue(s: str) -> str:
    return " ".join((s or "").lower().split())

def _save_attachment_if_any(request, work_order_id: int):
    imageFile = request.files.get("photo")

    if not imageFile or not imageFile.filename:
        return

    data = imageFile.read()

    root = current_app.config["ATTACHMENT_ROOT"]
    subdir = f"wo-{work_order_id}"
    os.makedirs(os.path.join(root, subdir), exist_ok=True)

    safe = secure_filename(imageFile.filename) or "upload"
    fileName = f"{int(time.time())}_{safe}"
    relativePath = os.path.join(subdir, fileName)

    with open(os.path.join(root, relativePath), "wb") as out:
        out.write(data)

    execute(
        "insert into attachment (work_order_id, storage_path, original_filename, mime_type)"+
        "values (%s,%s,%s, %s)",
        (work_order_id, relativePath, imageFile.filename, imageFile.mimetype)
    )

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
def create_issue(uuid_str:UUID):
    asset = query_one("select asset_id from asset where uuid=%s", (uuid_str,))
    if asset == None:
        abort(404)
    asset_id = asset[0]

    issue = (request.form.get("issue") or "").strip()
    if not issue:
        flash("Issue is required")
        return redirect(url_for("app.asset_page", uuid_str=uuid_str))

    # Check for recent issues, see if similar issues exist to avoid duplicates
    recent = query_one(
        "select work_order_id, raw_issue_description from work_order where asset_id = %s and status <> 'CLOSED' "
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
            _save_attachment_if_any(request, existing_id)
            _save_attachment_if_any()
            flash(f"Similar ticket exists; appended your report to WO-{existing_id}.")
            return redirect(url_for("app.asset_page", uuid_str=uuid_str))

    work_order_id = execute_returning_one(
        "insert into work_order (asset_id, status, raw_issue_description) values (%s, 'OPEN', %s) returning work_order_id",
        (asset_id, issue)
    )[0]
    _save_attachment_if_any(request, existing_id)
    flash(f"Opened Issue - {work_order_id}")
    return redirect(url_for("app.asset_page", uuid_str=uuid_str))

@bp.get("/attachments/<int:attachment_id>")
def attachment(attachment_id: int):
    row = query_one(
        "select storage_path, mime_type, original_filename from attachment where attachment_id = %s",
        (attachment_id,)
    )

    if not row:
        abort(404)

    relativePath, mime, originalName = row

    # harden path: ensure it stays under ATTACH_ROOT
    root = os.path.abspath(current_app.config["ATTACH_ROOT"])
    abspath = os.path.abspath(os.path.join(root, relativePath))
    if not abspath.startswith(root + os.sep):
        abort(403)

    directory = os.path.dirname(abspath)
    filename = os.path.basename(abspath)

    # TODO: switch to nginx or similar for prod
    # Inline by default (as_attachment=False). Flask ≥2.2: download_name
    return send_from_directory(
        directory,
        filename,
        mimetype=mime or None,
        as_attachment=False,
        download_name=originalName,
        conditional=True,  # supports Range/If-Modified-Since
        etag=True
    )

@bp.get("/issues/<int:work_order_id>")
def work_order_page(work_order_id: int):
    work_order = query_one(
        """
        select wo.work_order_id, wo.status, wo.raw_issue_description, wo.created_at, wo.closed_at, a.friendly_tag
        from work_order wo
        join asset a on a.asset_id = wo.asset_id
        where wo.work_order_id = %s
        """,
        (work_order_id,)
    )

    if not work_order:
        abort(404)
        #

    attachments = query_all(
        """
        select attachment_id, storage_path, mime_type, original_filename, uploaded_at
        from attachment
        where work_order_id = %s
        order by uploaded_at asc
        """,
        (work_order_id,)
    )

    return render_template("work_order.html", work_order=work_order, attachments=attachments)