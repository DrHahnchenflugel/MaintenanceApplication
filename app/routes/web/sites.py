from urllib.parse import urlsplit

from flask import abort, redirect, request, url_for

from app.services import sites as site_service

from . import bp as web_bp


def _safe_redirect_target(target: str | None) -> str | None:
    if not target:
        return None

    parts = urlsplit(target)
    if parts.scheme or parts.netloc:
        if parts.netloc and parts.netloc != request.host:
            return None

    if not parts.path.startswith("/"):
        return None

    safe_target = parts.path
    if parts.query:
        safe_target = f"{safe_target}?{parts.query}"
    if parts.fragment:
        safe_target = f"{safe_target}#{parts.fragment}"

    return safe_target


@web_bp.post("/set-site", strict_slashes=False)
def set_preferred_site():
    site_code = request.form.get("site_code")
    next_target = _safe_redirect_target(
        (request.form.get("next") or request.referrer or "").strip()
    )

    response = redirect(next_target or url_for("app.dashboard"))

    try:
        site_service.set_preferred_site_cookie(response, site_code)
    except ValueError as exc:
        abort(400, description=str(exc))

    return response
