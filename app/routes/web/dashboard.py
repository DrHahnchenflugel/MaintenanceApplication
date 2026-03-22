from datetime import datetime, timedelta, timezone

from flask import jsonify, render_template, url_for
from sqlalchemy import text

from app.db.connection import get_connection
from app.helpers import human_delta_2_times, human_delta_to_now
from app.routes.api.v2 import bp as api_v2_bp

from . import bp as web_bp


DOWN_ASSET_STATUS_CODE = "DOWN"
TREND_ROLLING_AVERAGE_DAYS = 14


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


def _get_dashboard_time_bounds(conn):
    sql = text("""
        SELECT
            CURRENT_DATE AS today,
            (CURRENT_DATE - INTERVAL '3 months')::date AS trend_start,
            date_trunc('week', CURRENT_DATE)::date AS week_start,
            (date_trunc('week', CURRENT_DATE)::date + INTERVAL '7 days')::date AS week_end
    """)

    row = conn.execute(sql).mappings().first()
    return dict(row) if row is not None else {
        "today": None,
        "trend_start": None,
        "week_start": None,
        "week_end": None,
    }


def _get_dashboard_overview(conn, *, week_start, week_end):
    sql = text("""
        WITH issue_counts AS (
            SELECT
                COUNT(*) FILTER (
                    WHERE issue_status.code IN ('OPEN', 'IN_PROGRESS')
                )::int AS open_issues,
                COUNT(*) FILTER (
                    WHERE issue_status.code = 'BLOCKED'
                )::int AS blocked_issues,
                COUNT(*) FILTER (
                    WHERE issue.created_at >= :week_start
                      AND issue.created_at < :week_end
                )::int AS opened_this_week,
                COUNT(*) FILTER (
                    WHERE issue.closed_at IS NOT NULL
                      AND issue.closed_at >= :week_start
                      AND issue.closed_at < :week_end
                )::int AS closed_this_week,
                AVG(EXTRACT(EPOCH FROM (issue.closed_at - issue.created_at))) FILTER (
                    WHERE issue.closed_at IS NOT NULL
                      AND issue.closed_at >= issue.created_at
                ) AS avg_resolution_seconds,
                COUNT(*) FILTER (
                    WHERE issue.closed_at IS NOT NULL
                      AND issue.closed_at >= issue.created_at
                )::int AS resolved_issue_count
            FROM issue
            LEFT JOIN issue_status
              ON issue_status.id = issue.status_id
        ),
        oldest_open_issue AS (
            SELECT
                issue.id AS issue_id,
                issue.asset_id,
                issue.title,
                issue.created_at,
                asset.asset_tag
            FROM issue
            LEFT JOIN issue_status
              ON issue_status.id = issue.status_id
            LEFT JOIN asset
              ON asset.id = issue.asset_id
            WHERE issue_status.code IN ('OPEN', 'IN_PROGRESS')
            ORDER BY issue.created_at ASC
            LIMIT 1
        ),
        asset_counts AS (
            SELECT
                COUNT(*) FILTER (
                    WHERE asset.retired_at IS NULL
                      AND asset_status.code = :down_asset_status_code
                )::int AS assets_down
            FROM asset
            LEFT JOIN asset_status
              ON asset_status.id = asset.status_id
        )
        SELECT
            issue_counts.open_issues,
            issue_counts.blocked_issues,
            asset_counts.assets_down,
            issue_counts.opened_this_week,
            issue_counts.closed_this_week,
            issue_counts.avg_resolution_seconds,
            issue_counts.resolved_issue_count,
            oldest_open_issue.issue_id,
            oldest_open_issue.asset_id AS oldest_asset_id,
            oldest_open_issue.asset_tag AS oldest_asset_tag,
            oldest_open_issue.title AS oldest_issue_title,
            oldest_open_issue.created_at AS oldest_issue_created_at
        FROM issue_counts
        CROSS JOIN asset_counts
        LEFT JOIN oldest_open_issue ON TRUE
    """)

    row = conn.execute(
        sql,
        {
            "week_start": week_start,
            "week_end": week_end,
            "down_asset_status_code": DOWN_ASSET_STATUS_CODE,
        },
    ).mappings().first()

    return dict(row) if row is not None else {}


def _get_repeat_offender(conn, *, window_start=None):
    where_sql = ""
    params = {}

    if window_start is not None:
        where_sql = "WHERE issue.created_at >= :window_start"
        params["window_start"] = window_start

    sql = text(f"""
        SELECT
            asset.id AS asset_id,
            asset.asset_tag,
            site.shorthand AS site_shorthand,
            COUNT(issue.id)::int AS issue_count,
            MAX(issue.created_at) AS last_issue_created_at,
            make.label AS make_label,
            make.name AS make_name,
            model.label AS model_label,
            model.name AS model_name,
            variant.label AS variant_label,
            variant.name AS variant_name
        FROM issue
        JOIN asset
          ON asset.id = issue.asset_id
        LEFT JOIN site
          ON site.id = asset.site_id
        LEFT JOIN variant
          ON variant.id = asset.variant_id
        LEFT JOIN model
          ON model.id = variant.model_id
        LEFT JOIN make
          ON make.id = model.make_id
        {where_sql}
        GROUP BY
            asset.id,
            asset.asset_tag,
            site.shorthand,
            make.label,
            make.name,
            model.label,
            model.name,
            variant.label,
            variant.name
        ORDER BY
            COUNT(issue.id) DESC,
            MAX(issue.created_at) DESC,
            asset.asset_tag ASC
        LIMIT 1
    """)

    row = conn.execute(sql, params).mappings().first()
    return dict(row) if row is not None else None


def _get_top_models_by_issue_rate(conn, *, window_start):
    sql = text("""
        WITH active_asset_counts AS (
            SELECT
                model.id AS model_id,
                make.label AS make_label,
                make.name AS make_name,
                model.label AS model_label,
                model.name AS model_name,
                COUNT(asset.id)::int AS asset_count
            FROM model
            LEFT JOIN make
              ON make.id = model.make_id
            LEFT JOIN variant
              ON variant.model_id = model.id
            LEFT JOIN asset
              ON asset.variant_id = variant.id
             AND asset.retired_at IS NULL
            GROUP BY
                model.id,
                make.label,
                make.name,
                model.label,
                model.name
        ),
        issue_counts AS (
            SELECT
                variant.model_id,
                COUNT(issue.id)::int AS issue_count
            FROM issue
            JOIN asset
              ON asset.id = issue.asset_id
            LEFT JOIN variant
              ON variant.id = asset.variant_id
            WHERE issue.created_at >= :window_start
            GROUP BY variant.model_id
        )
        SELECT
            active_asset_counts.model_id,
            active_asset_counts.make_label,
            active_asset_counts.make_name,
            active_asset_counts.model_label,
            active_asset_counts.model_name,
            active_asset_counts.asset_count,
            COALESCE(issue_counts.issue_count, 0)::int AS issue_count,
            CASE
                WHEN active_asset_counts.asset_count = 0 THEN NULL
                ELSE ROUND(
                    COALESCE(issue_counts.issue_count, 0)::numeric / active_asset_counts.asset_count,
                    4
                )
            END AS issue_rate
        FROM active_asset_counts
        LEFT JOIN issue_counts
          ON issue_counts.model_id = active_asset_counts.model_id
        WHERE COALESCE(issue_counts.issue_count, 0) > 0
        ORDER BY
            CASE WHEN active_asset_counts.asset_count = 0 THEN 1 ELSE 0 END ASC,
            CASE
                WHEN active_asset_counts.asset_count = 0 THEN NULL
                ELSE COALESCE(issue_counts.issue_count, 0)::numeric / active_asset_counts.asset_count
            END DESC NULLS LAST,
            COALESCE(issue_counts.issue_count, 0) DESC,
            COALESCE(active_asset_counts.model_label, active_asset_counts.model_name, '') ASC
        LIMIT 3
    """)

    rows = conn.execute(sql, {"window_start": window_start}).mappings().all()
    return [dict(row) for row in rows]


def _get_issue_trend_points(conn, *, trend_start, trend_end):
    sql = text("""
        WITH daily AS (
            SELECT generate_series(:trend_start::date, :trend_end::date, INTERVAL '1 day')::date AS day
        ),
        initial_events AS (
            SELECT
                issue.id AS issue_id,
                issue.created_at AS changed_at,
                COALESCE(
                    (
                        SELECT ish.from_status_id
                        FROM issue_status_history ish
                        WHERE ish.issue_id = issue.id
                          AND ish.from_status_id IS NOT NULL
                        ORDER BY ish.changed_at ASC
                        LIMIT 1
                    ),
                    (
                        SELECT ish.to_status_id
                        FROM issue_status_history ish
                        WHERE ish.issue_id = issue.id
                        ORDER BY ish.changed_at ASC
                        LIMIT 1
                    ),
                    issue.status_id
                ) AS status_id
            FROM issue
        ),
        history_events AS (
            SELECT
                issue_id,
                changed_at,
                to_status_id AS status_id
            FROM issue_status_history
        ),
        all_events AS (
            SELECT issue_id, changed_at, status_id
            FROM initial_events
            WHERE status_id IS NOT NULL

            UNION

            SELECT issue_id, changed_at, status_id
            FROM history_events
            WHERE status_id IS NOT NULL
        ),
        ordered_events AS (
            SELECT
                issue_id,
                status_id,
                changed_at,
                LEAD(changed_at) OVER (
                    PARTITION BY issue_id
                    ORDER BY changed_at, status_id
                ) AS next_changed_at
            FROM all_events
        ),
        daily_snapshots AS (
            SELECT
                daily.day,
                COUNT(*) FILTER (
                    WHERE issue_status.code IN ('OPEN', 'IN_PROGRESS')
                )::int AS open_count,
                COUNT(*) FILTER (
                    WHERE issue_status.code = 'BLOCKED'
                )::int AS blocked_count
            FROM daily
            LEFT JOIN ordered_events
              ON ordered_events.changed_at < (daily.day + INTERVAL '1 day')
             AND (
                    ordered_events.next_changed_at IS NULL
                 OR ordered_events.next_changed_at >= (daily.day + INTERVAL '1 day')
             )
            LEFT JOIN issue_status
              ON issue_status.id = ordered_events.status_id
            GROUP BY daily.day
        ),
        rolled AS (
            SELECT
                day,
                open_count,
                blocked_count,
                ROUND(
                    AVG(open_count) OVER (
                        ORDER BY day
                        ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
                    ),
                    2
                ) AS open_rolling_avg,
                ROUND(
                    AVG(blocked_count) OVER (
                        ORDER BY day
                        ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
                    ),
                    2
                ) AS blocked_rolling_avg
            FROM daily_snapshots
        )
        SELECT
            day,
            open_count,
            blocked_count,
            open_rolling_avg,
            blocked_rolling_avg
        FROM rolled
        ORDER BY day ASC
    """)

    rows = conn.execute(
        sql,
        {
            "trend_start": trend_start,
            "trend_end": trend_end,
        },
    ).mappings().all()

    return [dict(row) for row in rows]


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
        "issue_url": url_for("app.view_issue", issue_id=issue_id),
        "asset_url": url_for("app.view_asset", asset_id=asset_id) if asset_id is not None else None,
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
        "asset_url": url_for("app.view_asset", asset_id=asset_id) if asset_id is not None else None,
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


def _build_dashboard_payload():
    with get_connection() as conn:
        bounds = _get_dashboard_time_bounds(conn)
        overview = _get_dashboard_overview(
            conn,
            week_start=bounds["week_start"],
            week_end=bounds["week_end"],
        )
        repeat_all_time = _get_repeat_offender(conn)
        repeat_recent = _get_repeat_offender(
            conn,
            window_start=bounds["trend_start"],
        )
        problem_models = _get_top_models_by_issue_rate(
            conn,
            window_start=bounds["trend_start"],
        )
        trend_rows = _get_issue_trend_points(
            conn,
            trend_start=bounds["trend_start"],
            trend_end=bounds["today"],
        )

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


@api_v2_bp.get("/dashboard", strict_slashes=False)
def dashboard_data():
    return jsonify(_build_dashboard_payload())


@web_bp.get("/", strict_slashes=False)
@web_bp.get("/dashboard", strict_slashes=False)
def dashboard():
    return render_template(
        "dashboard/index.html",
        api_dashboard_url=url_for("api_v2.dashboard_data"),
    )
