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
def dashboard():
    return render_template("dashboard/index.html")

@bp.get("/issues/active")
def issues_active():
    issues = []
    return render_template("issues/active.html", issues=issues)
