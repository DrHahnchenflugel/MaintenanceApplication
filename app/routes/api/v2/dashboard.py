from flask import jsonify, url_for

from app.services import dashboard as dashboard_service

from . import bp


def _add_dashboard_links(payload):
    oldest_open_issue = payload.get("summary", {}).get("oldest_open_issue")
    if oldest_open_issue and oldest_open_issue.get("id"):
        oldest_open_issue["issue_url"] = url_for("app.view_issue", issue_id=oldest_open_issue["id"])
        if oldest_open_issue.get("asset_id"):
            oldest_open_issue["asset_url"] = url_for("app.view_asset", asset_id=oldest_open_issue["asset_id"])
        else:
            oldest_open_issue["asset_url"] = None

    repeat_offenders = payload.get("repeat_offenders", {})
    for key in ("all_time", "last_3_months"):
        offender = repeat_offenders.get(key)
        if offender and offender.get("asset_id"):
            offender["asset_url"] = url_for("app.view_asset", asset_id=offender["asset_id"])
        elif offender is not None:
            offender["asset_url"] = None

    return payload


@bp.get("/dashboard", strict_slashes=False)
def dashboard_data():
    return jsonify(_add_dashboard_links(dashboard_service.get_dashboard_data()))
