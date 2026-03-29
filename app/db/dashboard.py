from sqlalchemy import text

from app.db.connection import get_connection


def _site_filter_clause(column_name: str = "asset.site_id") -> str:
    return f"(:site_id IS NULL OR {column_name} = :site_id)"


def get_dashboard_time_bounds():
    sql = text("""
        SELECT
            CURRENT_DATE AS today,
            (CURRENT_DATE - INTERVAL '3 months')::date AS trend_start,
            date_trunc('week', CURRENT_DATE)::date AS week_start,
            (date_trunc('week', CURRENT_DATE)::date + INTERVAL '7 days')::date AS week_end
    """)

    with get_connection() as conn:
        row = conn.execute(sql).mappings().first()

    if row is None:
        return {
            "today": None,
            "trend_start": None,
            "week_start": None,
            "week_end": None,
        }

    return dict(row)


def get_dashboard_overview(*, week_start, week_end, site_id=None):
    site_filter = _site_filter_clause()

    sql = text(f"""
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
            LEFT JOIN asset
              ON asset.id = issue.asset_id
            WHERE {site_filter}
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
              AND {site_filter}
            ORDER BY issue.created_at ASC
            LIMIT 1
        ),
        asset_counts AS (
            SELECT
                COUNT(*) FILTER (
                    WHERE asset.retired_at IS NULL
                      AND (
                            UPPER(COALESCE(asset_status.code, '')) LIKE '%MAINTEN%'
                         OR UPPER(COALESCE(asset_status.label, '')) LIKE '%MAINTEN%'
                      )
                )::int AS assets_down
            FROM asset
            LEFT JOIN asset_status
              ON asset_status.id = asset.status_id
            WHERE {site_filter}
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

    with get_connection() as conn:
        row = conn.execute(
            sql,
            {
                "week_start": week_start,
                "week_end": week_end,
                "site_id": site_id,
            },
        ).mappings().first()

    if row is None:
        return {}

    return dict(row)


def get_repeat_offender(*, window_start=None, site_id=None):
    where_clauses = [
        "(asset_status.code IS NULL OR asset_status.code <> 'RETIRED')",
    ]
    params = {}

    if window_start is not None:
        where_clauses.append("issue.created_at >= :window_start")
        params["window_start"] = window_start

    if site_id is not None:
        where_clauses.append("asset.site_id = :site_id")
        params["site_id"] = site_id

    where_sql = f"WHERE {' AND '.join(where_clauses)}"

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
        LEFT JOIN asset_status
          ON asset_status.id = asset.status_id
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

    with get_connection() as conn:
        row = conn.execute(sql, params).mappings().first()

    if row is None:
        return None

    return dict(row)


def get_top_models_by_issue_rate(*, window_start, site_id=None):
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
             AND (:site_id IS NULL OR asset.site_id = :site_id)
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
              AND (:site_id IS NULL OR asset.site_id = :site_id)
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

    with get_connection() as conn:
        rows = conn.execute(
            sql,
            {
                "window_start": window_start,
                "site_id": site_id,
            },
        ).mappings().all()

    return [dict(row) for row in rows]


def get_issue_trend_rows(*, trend_start, trend_end, site_id=None):
    sql = text("""
        WITH daily AS (
            SELECT generate_series(:trend_start::date, :trend_end::date, INTERVAL '1 day')::date AS day
        ),
        scoped_issues AS (
            SELECT
                issue.id AS issue_id,
                issue.created_at,
                issue.status_id
            FROM issue
            JOIN asset
              ON asset.id = issue.asset_id
            WHERE (:site_id IS NULL OR asset.site_id = :site_id)
        ),
        initial_events AS (
            SELECT
                scoped_issues.issue_id,
                scoped_issues.created_at AS changed_at,
                COALESCE(
                    (
                        SELECT ish.from_status_id
                        FROM issue_status_history ish
                        WHERE ish.issue_id = scoped_issues.issue_id
                          AND ish.from_status_id IS NOT NULL
                        ORDER BY ish.changed_at ASC
                        LIMIT 1
                    ),
                    (
                        SELECT ish.to_status_id
                        FROM issue_status_history ish
                        WHERE ish.issue_id = scoped_issues.issue_id
                        ORDER BY ish.changed_at ASC
                        LIMIT 1
                    ),
                    scoped_issues.status_id
                ) AS status_id
            FROM scoped_issues
        ),
        history_events AS (
            SELECT
                issue_status_history.issue_id,
                issue_status_history.changed_at,
                issue_status_history.to_status_id AS status_id
            FROM issue_status_history
            JOIN scoped_issues
              ON scoped_issues.issue_id = issue_status_history.issue_id
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

    with get_connection() as conn:
        rows = conn.execute(
            sql,
            {
                "trend_start": trend_start,
                "trend_end": trend_end,
                "site_id": site_id,
            },
        ).mappings().all()

    return [dict(row) for row in rows]
