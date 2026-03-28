from flask import abort, jsonify, request

from . import bp
from app.services import auth as auth_service


def _debug(message: str, **fields):
    details = ", ".join(f"{key}={value!r}" for key, value in fields.items())
    if details:
        print(f"[admin_gate.route] {message} | {details}", flush=True)
        return

    print(f"[admin_gate.route] {message}", flush=True)


def _parse_gate_name(value):
    if not isinstance(value, str) or value.strip() == "":
        _debug("missing gate name", raw_value=value)
        abort(400, description="Missing required field: name")

    name = value.strip()
    if name != auth_service.SETTINGS_ADMIN_GATE_NAME:
        _debug("unknown gate name", name=name)
        abort(404, description="Admin gate not found")

    return name


def _parse_password(value):
    if not isinstance(value, str) or value == "":
        _debug(
            "missing password",
            password_type=type(value).__name__ if value is not None else None,
        )
        abort(400, description="Missing required field: password")

    return value


@bp.route("/auth/admin-gate/unlock", methods=["POST"])
def unlock_admin_gate():
    data = request.get_json(silent=True) or {}
    _debug(
        "unlock request received",
        path=request.path,
        content_type=request.content_type,
        payload_keys=sorted(data.keys()),
        raw_name=data.get("name"),
        has_password="password" in data,
        password_length=len(data.get("password")) if isinstance(data.get("password"), str) else None,
        incoming_cookie=request.cookies.get(auth_service.SETTINGS_ADMIN_GATE_COOKIE_NAME),
    )

    name = _parse_gate_name(data.get("name"))
    password = _parse_password(data.get("password"))

    if not auth_service.admin_gate_exists(name):
        _debug("unlock failed: gate missing", name=name)
        abort(404, description="Admin gate not found")

    if not auth_service.is_admin_gate_enabled(name):
        _debug("unlock failed: gate disabled", name=name)
        abort(403, description="Admin gate is disabled")

    if not auth_service.verify_admin_gate(name, password):
        _debug("unlock failed: password mismatch", name=name)
        return jsonify({"ok": False, "error": "Invalid password"}), 401

    response = jsonify({"ok": True})
    response.set_cookie(
        auth_service.SETTINGS_ADMIN_GATE_COOKIE_NAME,
        "1",
        httponly=False,
        samesite="Lax",
        path=auth_service.SETTINGS_ADMIN_GATE_COOKIE_PATH,
    )
    _debug(
        "unlock succeeded",
        name=name,
        response_cookie=response.headers.get("Set-Cookie"),
    )
    return response


@bp.route("/auth/admin-gate/lock", methods=["POST"])
def lock_admin_gate():
    _debug(
        "lock request received",
        path=request.path,
        incoming_cookie=request.cookies.get(auth_service.SETTINGS_ADMIN_GATE_COOKIE_NAME),
    )
    response = jsonify({"ok": True})
    response.set_cookie(
        auth_service.SETTINGS_ADMIN_GATE_COOKIE_NAME,
        "",
        expires=0,
        path=auth_service.SETTINGS_ADMIN_GATE_COOKIE_PATH,
    )
    _debug("lock response prepared", response_cookie=response.headers.get("Set-Cookie"))
    return response


@bp.route("/auth/admin-gate/status", methods=["GET"])
def admin_gate_status():
    name = _parse_gate_name(request.args.get("name"))
    _debug(
        "status request received",
        path=request.path,
        query_name=name,
        incoming_cookie=request.cookies.get(auth_service.SETTINGS_ADMIN_GATE_COOKIE_NAME),
    )

    if not auth_service.admin_gate_exists(name):
        _debug("status failed: gate missing", name=name)
        abort(404, description="Admin gate not found")

    unlocked = request.cookies.get(auth_service.SETTINGS_ADMIN_GATE_COOKIE_NAME) == "1"
    _debug("status resolved", name=name, unlocked=unlocked)

    return jsonify({
        "ok": True,
        "name": name,
        "unlocked": unlocked,
    })
