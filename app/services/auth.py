from werkzeug.security import check_password_hash
from flask import request

from app.db import auth as auth_db


SETTINGS_ADMIN_GATE_NAME = "settings"
SETTINGS_ADMIN_GATE_COOKIE_NAME = "admin_gate_settings"
SETTINGS_ADMIN_GATE_COOKIE_PATH = "/maintenance"


def _normalize_admin_gate_name(name: str | None) -> str:
    return (name or "").strip()


def admin_gate_exists(name: str) -> bool:
    normalized_name = _normalize_admin_gate_name(name)
    if not normalized_name:
        return False

    return auth_db.admin_gate_exists(normalized_name)


def is_admin_gate_enabled(name: str) -> bool:
    normalized_name = _normalize_admin_gate_name(name)
    if not normalized_name:
        return False

    return auth_db.is_admin_gate_enabled(normalized_name)


def verify_admin_gate(name: str, password: str) -> bool:
    normalized_name = _normalize_admin_gate_name(name)
    if not normalized_name or not isinstance(password, str) or password == "":
        return False

    row = auth_db.get_admin_gate_row(normalized_name)
    if row is None:
        return False

    if not row.get("is_enabled"):
        return False

    return check_password_hash(row["password_hash"], password)


def is_settings_admin_unlocked(req=None) -> bool:
    req = req or request
    return req.cookies.get(SETTINGS_ADMIN_GATE_COOKIE_NAME) == "1"
