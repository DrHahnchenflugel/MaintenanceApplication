import os, hashlib, time
from flask import Blueprint, jsonify, abort, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from .db import query_one, query_all, execute_returning_one, execute
from uuid import UUID
from datetime import datetime, timezone, timedelta
from werkzeug.utils import secure_filename
from .helpers import human_delta_to_now, human_delta_2_times

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
    num_open_issues_sql = query_one(
        """
            SELECT
            COUNT(*)
            FROM work_order
            WHERE status = 'OPEN'
                OR status = 'IN_PROGRESS';
        """
    )

    num_blocked_issues_sql = query_one(
        """
            SELECT
            COUNT(*)
            FROM work_order
            WHERE status = 'BLOCKED';
        """
    )

    oldest_issue_sql = query_one(
        """
            SELECT 
                created_at, raw_issue_description, work_order_id
            FROM work_order
            WHERE status IN ('OPEN', 'IN_PROGRESS') 
            ORDER BY created_at ASC
            LIMIT 1;
        """
    )
    if oldest_issue_sql:
        dt_utc = oldest_issue_sql[0]
        tz_minus_5 = timezone(timedelta(hours=-5))
        dt_local = dt_utc.astimezone(tz_minus_5)
        now_local = datetime.now(tz_minus_5)
        delta = now_local - dt_local
        days = delta.days
        hours = delta.seconds // 3600
        delta_time = f"{days} Days {hours} Hrs" if days else f"{hours}H"
    else:
        delta_time = "N/A"

    issue_info = {
        'num_open_issues' : num_open_issues_sql[0],
        'num_blocked_issues' : num_blocked_issues_sql[0],
        'oldest_issue' : delta_time
    }

    return render_template("dashboard/index.html", issue_info = issue_info)

@bp.get("/issues/active")
def issues_active():
    issues_sql = query_all("""SELECT (w.uuid, w.asset_id, w.raw_issue_description, w.created_at, w.status, 
                            a.friendly_tag, a.site_id, a.make, a.model, a.variant, a.status) 
                            FROM work_order w 
                            JOIN asset a 
                            ON w.asset_id = a.asset_id 
                            WHERE w.status IN ('OPEN', 'IN_PROGRESS') 
                            ORDER BY w.created_at DESC;""")
    issues = []
    for i in issues_sql:
        issues.append(
            {
                'workOrder_uuid':i[0][0],
                'workOrder_asset_id':i[0][1],
                'workOrder_raw_issue_description':i[0][2],
                'workOrder_created_at':i[0][3],
                'workOrder_status':i[0][4],
                'asset_friendly_tag':i[0][5],
                'asset_site_id':i[0][6],
                'asset_make':i[0][7],
                'asset_model':i[0][8],
                'asset_variant':i[0][9],
                'asset_status':i[0][10],
            }
        )

    return render_template("issues/active.html", issues=issues)

@bp.get("/issues/new")
def new_issue():
    assets_sql = query_all("""SELECT (a.uuid, a.friendly_tag, a.site_id, a.make, a.model, a.variant, a.status,
                        s.location_shorthand, s.friendly_name) 
                        FROM asset a
                        JOIN site s
                        ON a.site_id = s.site_id
                        ORDER BY friendly_tag ASC;
                        """)
    assets = []
    for asset in assets_sql:
        assets.append(
            {
                'asset_uuid':asset[0][0],
                'asset_friendly_tag':asset[0][1],
                'asset_site_id':asset[0][2],
                'asset_make':asset[0][3],
                'asset_model':asset[0][4],
                'asset_variant':asset[0][5],
                'asset_status':asset[0][6],
                'site_location_shorthand':asset[0][7],
                'site_friendly_name':asset[0][8]
            }
        )
    return render_template("issues/new_issue_asset_selector.html", assets=assets)

@bp.get("/issues/new/<uuid:asset_uuid>")
def new_issue_for_asset(asset_uuid):
    asset_sql = query_one("""SELECT 
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

    if asset_sql is None:
        abort(404)

    asset = {
        'asset_uuid':asset_sql[0],
        'asset_friendly_tag':asset_sql[1],
        'asset_site_id':asset_sql[2],
        'asset_make':asset_sql[3],
        'asset_model':asset_sql[4],
        'asset_variant':asset_sql[5],
        'asset_status':asset_sql[6],
        'site_location_shorthand':asset_sql[7],
        'site_friendly_name':asset_sql[8]
    }

    return render_template("issues/new.html", asset=asset, asset_uuid=asset_uuid, form={})

@bp.post("/issues/new/<uuid:asset_uuid>")
def create_issue_for_asset(asset_uuid):
    asset_sql = query_one("""SELECT 
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

    if asset_sql is None:
        abort(404)

    asset = {
        'asset_uuid': asset_sql[0],
        'asset_friendly_tag': asset_sql[1],
        'asset_site_id': asset_sql[2],
        'asset_make': asset_sql[3],
        'asset_model': asset_sql[4],
        'asset_variant': asset_sql[5],
        'asset_status': asset_sql[6],
        'site_location_shorthand': asset_sql[7],
        'site_friendly_name': asset_sql[8]
    }

    asset_id = asset.get('asset_uuid')
    description = (request.form.get("description") or "").strip()

    errors = []
    if not description:
        errors.append("Description is required.")

    if errors:
        for e in errors:
            flash(e, "error")

        asset_sql = query_one("""SELECT 
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

        if asset_sql is None:
            abort(404)

        asset = {
            'asset_uuid': asset_sql[0],
            'asset_friendly_tag': asset_sql[1],
            'asset_site_id': asset_sql[2],
            'asset_make': asset_sql[3],
            'asset_model': asset_sql[4],
            'asset_variant': asset_sql[5],
            'asset_status': asset_sql[6],
            'site_location_shorthand': asset_sql[7],
            'site_friendly_name': asset_sql[8]
        }

        return render_template(f"issues/new.html", asset=asset, asset_uuid=asset_uuid, form=request.form)

    workOrder = execute_returning_one("""
        INSERT INTO work_order (asset_id, raw_issue_description, status)
        VALUES (%s, %s, 'OPEN')
        RETURNING work_order_id;
        """, (asset_uuid, description))
    work_order_id = workOrder[0]

    execute("""
        INSERT INTO work_log (work_order_id, action_taken, result)
        VALUES (%s, 'Issue Opened.', 'Issue Opened.')
        RETURNING work_log_id;
        """, (work_order_id,))

    _save_attachment_if_any(request, work_order_id)

    flash("Issue created.", "ok")
    return redirect(url_for("app.issues_active", work_order_id=work_order_id))

@bp.get("/issues/<issue_uuid>")
def view_issue(issue_uuid):
    issue_sql = query_one(
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
            LEFT JOIN attachment att ON i.work_order_id = att.work_order_id
            WHERE i.uuid = %s;
        """, (issue_uuid,)
    )

    work_logs_sql = query_all(
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

    if issue_sql is None:
        abort(404)

    issue = {
        'work_order_id' : issue_sql[0],
        'asset_id' : issue_sql[1],
        'raw_issue_description' : issue_sql[2],
        'work_order_created_at' : issue_sql[3],
        'work_order_closed_at' : issue_sql[4],
        'work_order_close_note' : issue_sql[5],
        'work_order_status' : issue_sql[6],
        'work_order_uuid' : issue_sql[7],
        'asset_friendly_tag' : issue_sql[9],
        'asset_make' : issue_sql[11],
        'asset_model' : issue_sql[12],
        'asset_variant' : issue_sql[13],
        'asset_retired_at' : issue_sql[14],
        'asset_retired_reason' : issue_sql[15],
        'asset_status' : issue_sql[16],
        'attachment_id' : issue_sql[18],
        'attachment_storage_path' : issue_sql[20],
        'attachment_uploaded_at' : issue_sql[21],
        'attachment_mime_type' : issue_sql[22],
        'attachment_original_filename' : issue_sql[23],
        'site_id' : issue_sql[24],
        'site_location_shorthand' : issue_sql[25],
        'site_friendly_name' : issue_sql[26]
    }

    work_logs = []
    for log in work_logs_sql:
        work_logs.append(
            {
                'id':log[0],
                'action_taken':log[2],
                'result':log[3],
                'created_at':log[4]
            }
        )

    return render_template(f"issues/specific_issue.html", issue=issue, work_logs=work_logs)

@bp.post("/issues/<uuid:issue_uuid>/update")
def update_issue(issue_uuid):
    action_taken = request.form.get("action_taken", "").strip()
    result = request.form.get("result", "").strip()
    new_status = request.form.get("status", "").strip()

    # Find work_order_id from UUID
    wo = query_one("SELECT work_order_id FROM work_order WHERE uuid = %s", (str(issue_uuid),))
    if not wo:
        abort(404)
    work_order_id = wo[0]

    # Insert into work_log
    execute(
        """
        INSERT INTO work_log (work_order_id, action_taken, result)
        VALUES (%s, %s, %s)
        """,
        (work_order_id, action_taken, result)
    )

    if new_status in ['IN_PROGRESS', 'OPEN', 'CLOSED']:
        execute(
            "UPDATE work_order SET status = %s WHERE work_order_id = %s",
            (new_status, work_order_id)
        )
    elif new_status in ['BLOCKED']: #TODO: add something to blocked
        execute(
            "UPDATE work_order SET status = 'BLOCKED' WHERE work_order_id = %s",
            (work_order_id,)
        )

    flash("Updated issue log.", "ok")
    return redirect(url_for("app.view_issue", issue_uuid=issue_uuid))

@bp.get("/attachments/<path:subpath>")
def serve_attachment(subpath: str):
    root = os.path.abspath(current_app.config["ATTACHMENT_ROOT"])

    # Prevent path traversal
    full = os.path.abspath(os.path.join(root, subpath))
    if not full.startswith(root + os.sep) and full != root:
        abort(404)

    # Let Flask set Content-Type; don’t force download (we want inline images)
    resp = send_from_directory(root, subpath, as_attachment=False, conditional=True)
    resp.cache_control.public = True
    resp.cache_control.max_age = 86400  # 1 day
    return resp

@bp.get("/assets")
def assets():
    assets_sql = query_all(
        """
        SELECT 
            a.asset_id,
            a.friendly_tag,
            a.make,
            a.model,
            a.variant,
            a.status,
            a.uuid,
            s.location_shorthand,
            s.friendly_name
        
        FROM
            asset a
            JOIN site s ON a.site_id = s.site_id;
        """
    )

    assets = []
    for a in assets_sql:
        assets.append(
            {
                'asset_id' : a[0],
                'asset_friendly_tag' : a[1],
                'asset_make' : a[2],
                'asset_model' : a[3],
                'asset_variant' : a[4],
                'asset_status' : a[5],
                'asset_uuid' : a[6],
                'site_location_shorthand' : a[7],
                'site_friendly_name' : a[8]
            }
        )

    return render_template(f"assets/viewAssets.html", assets=assets)

@bp.get("/assets/<uuid:asset_uuid>")
def view_asset(asset_uuid):
    asset_sql = query_one(
        """
            SELECT 
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
                a.created_at,
                s.site_id,
                s.location_shorthand,
                s.friendly_name
            FROM asset a
            JOIN site s ON a.site_id = s.site_id
            WHERE a.uuid = %s;
        """,
        (asset_uuid, )
    )

    dt_utc = asset_sql[10]
    delta_time = human_delta_to_now(dt_utc=dt_utc)

    asset = {
        'asset_asset_id' : asset_sql[0],
        'asset_friendly_tag' : asset_sql[1],
        'asset_site_id' : asset_sql[2],
        'asset_make' : asset_sql[3],
        'asset_model' : asset_sql[4],
        'asset_variant' :  asset_sql[5],
        'asset_retired_at' : asset_sql[6],
        'asset_retired_reason' : asset_sql[7],
        'asset_status' : asset_sql[8],
        'asset_uuid' : asset_sql[9],
        'asset_age' : delta_time,
        'site_site_id' : asset_sql[11],
        'site_location_shorthand' : asset_sql[12],
        'site_friendly_name' : asset_sql[13]
    }

    inactive_issues_sorted_sql = query_all(
        """
            SELECT 
                work_order_id,
                asset_id,
                raw_issue_description,
                created_at,
                closed_at,
                close_note,
                status,
                uuid
            FROM 
                work_order
            WHERE
                asset_id = %s AND status = 'CLOSED'
            ORDER BY closed_at DESC;
        """,
        (asset.get('asset_asset_id'),)
    )

    active_issues_sorted_sql = query_all(
        """
            SELECT
                work_order_id,
                asset_id,
                raw_issue_description,
                created_at,
                status,
                uuid
            FROM 
                work_order
            WHERE
                asset_id = %s AND status <> 'CLOSED'
            ORDER BY created_at DESC;
        """,
        (asset.get('asset_asset_id'),)
    )

    issues = []
    for i in active_issues_sorted_sql:
        issues.append(
            {
                'date':i[3],
                'issue':i[2],
                'length':human_delta_to_now(i[3]),
                'result':i[4],
                'issue_uuid':i[5]
            }
        )

    for i in inactive_issues_sorted_sql:
        issues.append(
            {
                'date':i[3],
                'issue':i[2],
                'length':human_delta_2_times(i[3],i[4]) if i[4] else "NA",
                'result':i[5],
                'issue_uuid':i[7]
            }
        )

    return render_template('assets/specific_asset.html', asset = asset, issues = issues)


@bp.post("/assets/<uuid:asset_uuid>/update")
def update_asset(asset_uuid):
    make    = (request.form.get("asset_make") or "").strip()
    model   = (request.form.get("asset_model") or "").strip()
    variant = (request.form.get("asset_variant") or "").strip()

    row = query_one("SELECT asset_id FROM asset WHERE uuid = %s", (asset_uuid,))
    if row is None:
        abort(404)

    execute("""
        UPDATE asset
           SET make   = %s,
               model  = %s,
               variant= %s,
               modified_at  = NOW()
         WHERE uuid = %s
    """, (make, model, variant, asset_uuid))

    try:
        flash("Asset updated.", "success")
    except Exception:
        print("no flash :(")
        pass

    return redirect(url_for("app.view_asset", asset_uuid=asset_uuid))