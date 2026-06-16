from urllib.parse import urlsplit

from flask import abort, make_response, redirect, render_template, request, url_for

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


def _request_target() -> str:
    return request.full_path if request.query_string else request.path


def _next_target_from_request(raw_target: str | None) -> str:
    return _safe_redirect_target((raw_target or "").strip()) or url_for("app.dashboard")


@web_bp.before_request
def maintenance_location_guard():
    if request.method != "GET":
        return None

    if not site_service.should_show_maintenance_splash(request.endpoint):
        return None

    next_target = _next_target_from_request(_request_target())

    if not site_service.has_seen_maintenance_splash():
        return redirect(url_for("app.maintenance_welcome", next=next_target))

    if not site_service.has_confirmed_site_context():
        return redirect(url_for("app.choose_location", next=next_target))

    return None


@web_bp.get("/welcome", strict_slashes=False)
def maintenance_welcome():
    next_target = _next_target_from_request(request.args.get("next"))
    continue_url = next_target

    if not site_service.has_confirmed_site_context():
        continue_url = url_for("app.choose_location", next=next_target)

    response = make_response(
        render_template(
            "maintenance_welcome.html",
            continue_url=continue_url,
            splash_storage_key=site_service.MAINTENANCE_SPLASH_STORAGE_KEY,
        )
    )
    site_service.mark_maintenance_splash_seen(response)
    return response


@web_bp.route("/locations/select", methods=["GET"], strict_slashes=False)
def choose_location():
    return render_template(
        "choose_location.html",
        next_url=_next_target_from_request(request.args.get("next")),
        site_context_confirmed=site_service.has_confirmed_site_context(),
    )


@web_bp.route("/locations/select", methods=["POST"], strict_slashes=False)
def set_selected_location():
    selection_mode = (request.form.get("selection_mode") or "").strip().lower()
    site_code = request.form.get("site_code")
    next_target = _next_target_from_request(request.form.get("next"))

    if not selection_mode:
        selection_mode = "site" if (site_code or "").strip() else ""

    if selection_mode not in {"all", "site"}:
        abort(400, description="Invalid location selection.")

    if selection_mode == "site" and not (site_code or "").strip():
        abort(400, description="Please choose a valid site.")

    response = redirect(next_target)

    try:
        site_service.set_preferred_site_cookie(
            response,
            site_code if selection_mode == "site" else None,
        )
    except ValueError as exc:
        abort(400, description=str(exc))

    return response


@web_bp.post("/locations/clear", strict_slashes=False)
def clear_selected_location():
    next_target = _safe_redirect_target(
        (request.form.get("next") or request.referrer or "").strip()
    ) or url_for("app.choose_location")
    response = redirect(next_target)
    site_service.reset_preferred_site_selection(response)
    return response


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
