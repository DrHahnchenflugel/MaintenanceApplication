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

@bp.get("/")
@bp.get("/dashboard")
def dashboard():
    return render_template("dashboard/index.html")

@bp.get("/issues/active")
def issues_active():
    issues = query_all("""SELECT (w.work_order_id, w.asset_id, w.raw_issue_description, w.created_at, w.status, 
                            a.friendly_tag, a.site_id, a.make, a.model, a.variant, a.status) 
                            FROM work_order w 
                            JOIN asset a 
                            ON w.asset_id = a.asset_id 
                            WHERE w.status = 'OPEN' 
                            ORDER BY w.created_at DESC;""")
    return render_template("issues/active.html", issues=issues)

@bp.get("/issues/new")
def new_issue():
    assets = query_all("""SELECT (a.uuid, a.friendly_tag, a.site_id, a.make, a.model, a.variant, a.status,
                        s.location_shorthand, s.friendly_name) 
                        FROM asset a
                        JOIN site s
                        ON a.site_id = s.site_id
                        ORDER BY friendly_tag ASC;
                        """)

    return render_template("issues/new_issue_asset_selector.html", assets=assets)

@bp.get("/issues/new/<uuid:asset_uuid>")
def new_issue_for_asset(asset_uuid):
    asset = query_one("""SELECT (a.uuid, a.friendly_tag, a.site_id, a.make, a.model, a.variant, a.status,
                        s.location_shorthand, s.friendly_name) 
                        FROM asset a
                        JOIN site s
                        ON a.site_id = s.site_id
                        WHERE a.uuid = %s;
                        """, (str(asset_uuid),))
    if asset is None:
        abort(404)

    return render_template("issues/new.html", asset=asset, form={})

@bp.post("/issues/new/<uuid:asset_uuid>")
def create_issue_for_asset(asset_uuid):
    asset = query_one("select friendly_tag, site_id, make, model, variant, status from asset where uuid = %s;", (str(asset_uuid),))
    if asset is None:
        abort(404)
    asset_id = asset[0]

    description = (request.form.get("description") or "").strip()

    errors = []
    if not description:
        errors.append("Description is required.")

    if errors:
        for e in errors:
            flash(e, "error")

        # Re-render with entered values
        asset = query_one("""
            select friendly_tag, site_id, make, model, variant, status where from asset where uuid = %s;
            """, (str(asset_uuid),))
        print(f"returning w asset id {asset_uuid}")
        return render_template(f"issues/new/{asset_uuid}.html", asset=asset, form=request.form)

    row = execute_returning_one("""
        insert into work_order (asset_id, raw_issue_description, status)
        values (%s, %s, 'OPEN')
        returning work_order_id;
        """, (asset_id, description))

    work_order_id = row[0]

    _save_attachment_if_any(request, work_order_id)

    flash("Issue created.", "ok")
    return redirect(url_for("app.issues_active", work_order_id=work_order_id))
