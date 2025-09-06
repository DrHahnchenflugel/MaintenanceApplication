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
    issues = query_all("""SELECT (w.uuid, w.asset_id, w.raw_issue_description, w.created_at, w.status, 
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
    asset = query_one("""SELECT 
                                a.uuid, 
                                a.friendly_tag, 
                                a.site_id, 
                                a.make, 
                                a.model, 
                                a.variant, 
                                a.status,
                                
                                s.location_shorthand, 
                                s.friendly_name 

                                FROM asset a
                                JOIN site s
                                ON a.site_id = s.site_id
                                WHERE a.uuid = %s;
                                """,
                      (str(asset_uuid),))
    if asset is None:
        abort(404)

    return render_template("issues/new.html", asset=asset, asset_uuid=asset_uuid, form={})

@bp.post("/issues/new/<uuid:asset_uuid>")
def create_issue_for_asset(asset_uuid):

    asset = query_one("""
        SELECT 
            a.asset_id,           
            a.uuid,               
            a.friendly_tag,       
            a.site_id,            
            a.make,               
            a.model,              
            a.variant,            
            a.status,             
            s.location_shorthand, 
            s.friendly_name       
        FROM asset a
        JOIN site s ON a.site_id = s.site_id
        WHERE a.uuid = %s;
    """,
                      (str(asset_uuid),))
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

        asset = query_one("""
                SELECT 
                    a.asset_id,           
                    a.uuid,               
                    a.friendly_tag,       
                    a.site_id,            
                    a.make,               
                    a.model,              
                    a.variant,            
                    a.status,             
                    s.location_shorthand, 
                    s.friendly_name       
                FROM asset a
                JOIN site s ON a.site_id = s.site_id
                WHERE a.uuid = %s;
                """,
                (str(asset_uuid),))

        return render_template(f"issues/new.html", asset=asset, asset_uuid=asset_uuid, form=request.form)

    workOrder = execute_returning_one("""
        INSERT INTO work_order (asset_id, raw_issue_description, status)
        VALUES (%s, %s, 'OPEN')
        RETURNING work_order_id;
        """, (asset_id, description))
    work_order_id = workOrder[0]

    execute("""
        INSERT INTO work_log (work_order_id, action_taken)
        VALUES (%s, 'Issue Opened.')
        RETURNING work_log_id;
        """, (work_order_id,))

    _save_attachment_if_any(request, work_order_id)

    flash("Issue created.", "ok")
    return redirect(url_for("app.issues_active", work_order_id=work_order_id))

@bp.get("/issues/<issue_uuid>")
def view_issue(issue_uuid):
    issue = query_one(
        """
        SELECT
            i.work_order_id,
            i.asset_id,
            i.raw_issue_description,
            i.created_at,
            i.closed_at,
            i.close_note,
            i.status,
            i.uuid,
            a.asset_id,
            a.friendly_tag,
            a.site_id,
            a.make,
            a.model,
            a.variant,
            a.retired_at,
            a.retired_reason,
            a.status,
            a.uuid,
            att.attachment_id,
            att.work_order_id,
            att.storage_path,
            att.uploaded_at,
            att.mime_type,
            att.original_filename,
            s.site_id,
            s.location_shorthand,
            s.friendly_name
            FROM work_order i
            JOIN asset a ON i.asset_id = a.asset_id
            JOIN site s ON a.site_id = s.site_id
            JOIN work_log wl ON wl.work_order_id = i.work_order_id
            LEFT JOIN attachment att ON i.work_order_id = att.work_order_id
            WHERE i.uuid = %s;
        """, (issue_uuid,)
    )

    work_logs = query_all(
        """
            SELECT
            wl.work_log_id,
            wl.work_order_id,
            wl.action_taken,
            wl.result,
            wl.created_at
            
            FROM work_log wl
            JOIN work_order wo ON wl.work_order_id = wo.work_order_id
            WHERE wo.uuid = %s;
        """, (issue_uuid,)
    )

    if issue is None:
        print("no issue found")
        abort(404)

    return render_template(f"issues/specific_issue.html", issue=issue, work_logs=work_logs)

@bp.get("/attachments/<path:subpath>")
def serve_attachment(subpath: str):
    # ATTACHMENT_ROOT should be an absolute path
    root = os.path.abspath(current_app.config["ATTACHMENT_ROOT"])

    # Prevent path traversal
    full = os.path.abspath(os.path.join(root, subpath))
    if not full.startswith(root + os.sep) and full != root:
        abort(404)

    # Let Flask set Content-Type; don’t force download (we want inline images)
    resp = send_from_directory(root, subpath, as_attachment=False, conditional=True)
    # Optional: basic caching for images
    resp.cache_control.public = True
    resp.cache_control.max_age = 86400  # 1 day
    return resp
