from flask import abort, jsonify, request

from . import bp
from app.services import auth as auth_service


def _parse_gate_name(value):
    if not isinstance(value, str) or value.strip() == "":
        abort(400, description="Missing required field: name")

    name = value.strip()
    if name != auth_service.SETTINGS_ADMIN_GATE_NAME:
        abort(404, description="Admin gate not found")

    return name


def _parse_password(value):
    if not isinstance(value, str) or value == "":
        abort(400, description="Missing required field: password")

    return value


@bp.route("/auth/admin-gate/unlock", methods=["POST"])
def unlock_admin_gate():
    data = request.get_json(silent=True) or {}

    name = _parse_gate_name(data.get("name"))
    password = _parse_password(data.get("password"))

    if not auth_service.admin_gate_exists(name):
        abort(404, description="Admin gate not found")

    if not auth_service.is_admin_gate_enabled(name):
        abort(403, description="Admin gate is disabled")

    if not auth_service.verify_admin_gate(name, password):
        return jsonify({"ok": False, "error": "Invalid password"}), 401

    response = jsonify({"ok": True})
    response.set_cookie(
        auth_service.SETTINGS_ADMIN_GATE_COOKIE_NAME,
        "1",
        httponly=False,
        samesite="Lax",
        path=auth_service.SETTINGS_ADMIN_GATE_COOKIE_PATH,
    )
    return response


@bp.route("/auth/admin-gate/lock", methods=["POST"])
def lock_admin_gate():
    response = jsonify({"ok": True})
    response.set_cookie(
        auth_service.SETTINGS_ADMIN_GATE_COOKIE_NAME,
        "",
        expires=0,
        path=auth_service.SETTINGS_ADMIN_GATE_COOKIE_PATH,
    )
    return response


@bp.route("/auth/admin-gate/status", methods=["GET"])
def admin_gate_status():
    name = _parse_gate_name(request.args.get("name"))

    if not auth_service.admin_gate_exists(name):
        abort(404, description="Admin gate not found")

    unlocked = request.cookies.get(auth_service.SETTINGS_ADMIN_GATE_COOKIE_NAME) == "1"

    return jsonify({
        "ok": True,
        "name": name,
        "unlocked": unlocked,
    })
