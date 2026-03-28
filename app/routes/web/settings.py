from flask import render_template, request

from . import bp as web_bp
from app.services import auth as auth_service


@web_bp.get("/settings", strict_slashes=False)
def settings():
    settings_unlocked = (
        request.cookies.get(auth_service.SETTINGS_ADMIN_GATE_COOKIE_NAME) == "1"
    )

    return render_template(
        "settings/index.html",
        settings_unlocked=settings_unlocked,
    )
