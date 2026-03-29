import logging

from flask import jsonify, url_for

from app.services import dashboard as dashboard_service
from app.services import sites as site_service

from . import bp

logger = logging.getLogger(__name__)


def _fallback_dashboard_payload():
    return {
        "generated_at": None,
        "summary": {
            "open_issues": 0,
            "blocked_issues": 0,
            "assets_down": 0,
            "oldest_open_issue": None,
        },
        "throughput": {
            "week_start": None,
            "week_end_exclusive": None,
            "opened_this_week": 0,
            "closed_this_week": 0,
        },
        "resolution": {
            "average_resolution_seconds": None,
            "average_resolution_display": None,
            "resolved_issue_count": 0,
        },
        "repeat_offenders": {
            "all_time": None,
            "last_3_months": None,
        },
        "problem_models": [],
        "trend": {
            "window_start": None,
            "window_end": None,
            "rolling_average_days": 14,
            "points": [],
        },
    }


def _add_dashboard_links(payload):
    oldest_open_issue = payload.get("summary", {}).get("oldest_open_issue")
    if oldest_open_issue and oldest_open_issue.get("id"):
        try:
            oldest_open_issue["issue_url"] = url_for("app.view_issue", issue_id=oldest_open_issue["id"])
        except Exception:
            logger.exception("Failed building oldest-open issue URL for dashboard.")
            oldest_open_issue["issue_url"] = None

        if oldest_open_issue.get("asset_id"):
            try:
                oldest_open_issue["asset_url"] = url_for("app.view_asset", asset_id=oldest_open_issue["asset_id"])
            except Exception:
                logger.exception("Failed building oldest-open asset URL for dashboard.")
                oldest_open_issue["asset_url"] = None
        else:
            oldest_open_issue["asset_url"] = None

    repeat_offenders = payload.get("repeat_offenders", {})
    for key in ("all_time", "last_3_months"):
        offender = repeat_offenders.get(key)
        if offender and offender.get("asset_id"):
            try:
                offender["asset_url"] = url_for("app.view_asset", asset_id=offender["asset_id"])
            except Exception:
                logger.exception("Failed building repeat-offender asset URL for dashboard key=%s.", key)
                offender["asset_url"] = None
        elif offender is not None:
            offender["asset_url"] = None

    return payload


@bp.get("/dashboard", strict_slashes=False)
def dashboard_data():
    current_site = site_service.get_current_site() or {}
    site_id = current_site.get("id")

    try:
        payload = dashboard_service.get_dashboard_data(site_id=site_id)
    except Exception:
        logger.exception("Dashboard API failed building dashboard payload; returning fallback payload.")
        payload = _fallback_dashboard_payload()

    try:
        payload = _add_dashboard_links(payload)
    except Exception:
        logger.exception("Dashboard API failed adding dashboard links; returning payload without links.")

    return jsonify(payload)
