from werkzeug.security import check_password_hash

from app.db import auth as auth_db


SETTINGS_ADMIN_GATE_NAME = "settings"
SETTINGS_ADMIN_GATE_COOKIE_NAME = "admin_gate_settings"
SETTINGS_ADMIN_GATE_COOKIE_PATH = "/maintenance"


def _debug(message: str, **fields):
    details = ", ".join(f"{key}={value!r}" for key, value in fields.items())
    if details:
        print(f"[admin_gate.service] {message} | {details}", flush=True)
        return

    print(f"[admin_gate.service] {message}", flush=True)


def _normalize_admin_gate_name(name: str | None) -> str:
    return (name or "").strip()


def admin_gate_exists(name: str) -> bool:
    normalized_name = _normalize_admin_gate_name(name)
    if not normalized_name:
        _debug("admin_gate_exists skipped: empty name")
        return False

    exists = auth_db.admin_gate_exists(normalized_name)
    _debug("admin_gate_exists checked", name=normalized_name, exists=exists)
    return exists


def is_admin_gate_enabled(name: str) -> bool:
    normalized_name = _normalize_admin_gate_name(name)
    if not normalized_name:
        _debug("is_admin_gate_enabled skipped: empty name")
        return False

    enabled = auth_db.is_admin_gate_enabled(normalized_name)
    _debug("is_admin_gate_enabled checked", name=normalized_name, enabled=enabled)
    return enabled


def verify_admin_gate(name: str, password: str) -> bool:
    normalized_name = _normalize_admin_gate_name(name)
    if not normalized_name or not isinstance(password, str) or password == "":
        _debug(
            "verify_admin_gate rejected invalid input",
            name=normalized_name,
            password_type=type(password).__name__,
            password_length=len(password) if isinstance(password, str) else None,
        )
        return False

    _debug(
        "verify_admin_gate started",
        name=normalized_name,
        password_length=len(password),
    )
    row = auth_db.get_admin_gate_row(normalized_name)
    if row is None:
        _debug("verify_admin_gate failed: gate row missing", name=normalized_name)
        return False

    if not row.get("is_enabled"):
        _debug("verify_admin_gate failed: gate disabled", name=normalized_name)
        return False

    password_ok = check_password_hash(row["password_hash"], password)
    _debug("verify_admin_gate finished", name=normalized_name, password_ok=password_ok)
    return password_ok
