from flask import render_template, request

from . import bp as web_bp
from app.services import auth as auth_service


@web_bp.get("/settings", strict_slashes=False)
def settings():
    raw_cookie = request.cookies.get(auth_service.SETTINGS_ADMIN_GATE_COOKIE_NAME)
    settings_unlocked = raw_cookie == "1"
    print(
        "[admin_gate.web] settings page rendered"
        f" | path={request.path!r},"
        f" cookie_name={auth_service.SETTINGS_ADMIN_GATE_COOKIE_NAME!r},"
        f" cookie_value={raw_cookie!r},"
        f" unlocked={settings_unlocked!r}",
        flush=True,
    )

    return render_template(
        "settings/index.html",
        settings_unlocked=settings_unlocked,
    )
