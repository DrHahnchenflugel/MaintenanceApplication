import logging
from datetime import datetime, timedelta, timezone

from app.db import dashboard as dashboard_db
from app.helpers import human_delta_2_times, human_delta_to_now


TREND_ROLLING_AVERAGE_DAYS = 14
logger = logging.getLogger(__name__)


def _pick_label(*values):
    for value in values:
        if value is None:
            continue
        text_value = str(value).strip()
        if text_value:
            return text_value
    return None


def _join_parts(*values):
    parts = []
    for value in values:
        label = _pick_label(value)
        if label:
            parts.append(label)
    return " / ".join(parts)


def _to_iso(value):
    return value.isoformat() if value is not None else None


def _format_duration_from_seconds(total_seconds):
    if total_seconds is None:
        return None

    safe_seconds = max(int(round(float(total_seconds))), 0)
    anchor = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return human_delta_2_times(anchor, anchor + timedelta(seconds=safe_seconds))


def _serialize_oldest_open_issue(row):
    issue_id = row.get("issue_id")
    if issue_id is None:
        return None

    created_at = row.get("oldest_issue_created_at")
    asset_id = row.get("oldest_asset_id")

    return {
        "id": str(issue_id),
        "title": row.get("oldest_issue_title"),
        "asset_id": str(asset_id) if asset_id is not None else None,
        "asset_tag": row.get("oldest_asset_tag"),
        "created_at": _to_iso(created_at),
        "age_display": human_delta_to_now(created_at) if created_at is not None else None,
    }


def _serialize_repeat_offender(row):
    if row is None:
        return None

    asset_id = row.get("asset_id")
    asset_display = _pick_label(row.get("asset_tag")) or "Unknown Asset"
    model_display = _join_parts(
        _pick_label(row.get("make_label"), row.get("make_name")),
        _pick_label(row.get("model_label"), row.get("model_name")),
        _pick_label(row.get("variant_label"), row.get("variant_name")),
    )

    return {
        "asset_id": str(asset_id) if asset_id is not None else None,
        "asset_tag": row.get("asset_tag"),
        "asset_display": asset_display,
        "issue_count": int(row.get("issue_count") or 0),
        "site_shorthand": row.get("site_shorthand"),
        "model_display": model_display,
        "last_issue_created_at": _to_iso(row.get("last_issue_created_at")),
    }


def _serialize_problem_model(row):
    model_id = row.get("model_id")
    rate_value = row.get("issue_rate")
    issue_rate = round(float(rate_value), 2) if rate_value is not None else None
    display_name = _join_parts(
        _pick_label(row.get("make_label"), row.get("make_name")),
        _pick_label(row.get("model_label"), row.get("model_name")),
    ) or "Unknown Model"

    return {
        "model_id": str(model_id) if model_id is not None else None,
        "label": display_name,
        "asset_count": int(row.get("asset_count") or 0),
        "issue_count": int(row.get("issue_count") or 0),
        "issue_rate": issue_rate,
        "issue_rate_display": f"{issue_rate:.2f}" if issue_rate is not None else None,
    }


def _safe_bounds():
    fallback_today = datetime.now(timezone.utc).date()
    fallback_week_start = fallback_today - timedelta(days=fallback_today.weekday())
    fallback_week_end = fallback_week_start + timedelta(days=7)
    fallback_trend_start = fallback_today - timedelta(days=90)

    try:
        bounds = dashboard_db.get_dashboard_time_bounds() or {}
    except Exception:
        logger.exception("Dashboard time-bounds query failed; using fallback bounds.")
        bounds = {}

    return {
        "today": bounds.get("today") or fallback_today,
        "trend_start": bounds.get("trend_start") or fallback_trend_start,
        "week_start": bounds.get("week_start") or fallback_week_start,
        "week_end": bounds.get("week_end") or fallback_week_end,
    }


def get_dashboard_data(site_id: str | None = None):
    bounds = _safe_bounds()

    try:
        overview = dashboard_db.get_dashboard_overview(
            week_start=bounds["week_start"],
            week_end=bounds["week_end"],
            site_id=site_id,
        ) or {}
    except Exception:
        logger.exception("Dashboard overview query failed; returning default summary values.")
        overview = {}

    try:
        repeat_all_time = dashboard_db.get_repeat_offender(site_id=site_id)
    except Exception:
        logger.exception("Dashboard repeat-offender all-time query failed.")
        repeat_all_time = None

    try:
        repeat_recent = dashboard_db.get_repeat_offender(
            window_start=bounds["trend_start"],
            site_id=site_id,
        )
    except Exception:
        logger.exception("Dashboard repeat-offender recent query failed.")
        repeat_recent = None

    try:
        problem_models = dashboard_db.get_top_models_by_issue_rate(
            window_start=bounds["trend_start"],
            site_id=site_id,
        )
    except Exception:
        logger.exception("Dashboard top-models query failed; returning empty list.")
        problem_models = []

    try:
        trend_rows = dashboard_db.get_issue_trend_rows(
            trend_start=bounds["trend_start"],
            trend_end=bounds["today"],
            site_id=site_id,
        )
    except Exception:
        logger.exception("Dashboard trend query failed; returning empty trend data.")
        trend_rows = []

    avg_resolution_seconds = overview.get("avg_resolution_seconds")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "open_issues": int(overview.get("open_issues") or 0),
            "blocked_issues": int(overview.get("blocked_issues") or 0),
            "assets_down": int(overview.get("assets_down") or 0),
            "oldest_open_issue": _serialize_oldest_open_issue(overview),
        },
        "throughput": {
            "week_start": _to_iso(bounds.get("week_start")),
            "week_end_exclusive": _to_iso(bounds.get("week_end")),
            "opened_this_week": int(overview.get("opened_this_week") or 0),
            "closed_this_week": int(overview.get("closed_this_week") or 0),
        },
        "resolution": {
            "average_resolution_seconds": (
                max(int(round(float(avg_resolution_seconds))), 0)
                if avg_resolution_seconds is not None
                else None
            ),
            "average_resolution_display": _format_duration_from_seconds(avg_resolution_seconds),
            "resolved_issue_count": int(overview.get("resolved_issue_count") or 0),
        },
        "repeat_offenders": {
            "all_time": _serialize_repeat_offender(repeat_all_time),
            "last_3_months": _serialize_repeat_offender(repeat_recent),
        },
        "problem_models": [
            _serialize_problem_model(row)
            for row in problem_models
        ],
        "trend": {
            "window_start": _to_iso(bounds.get("trend_start")),
            "window_end": _to_iso(bounds.get("today")),
            "rolling_average_days": TREND_ROLLING_AVERAGE_DAYS,
            "points": [
                {
                    "date": _to_iso(row.get("day")),
                    "open_count": int(row.get("open_count") or 0),
                    "blocked_count": int(row.get("blocked_count") or 0),
                    "open_rolling_avg": round(float(row.get("open_rolling_avg") or 0), 2),
                    "blocked_rolling_avg": round(float(row.get("blocked_rolling_avg") or 0), 2),
                }
                for row in trend_rows
            ],
        },
    }
