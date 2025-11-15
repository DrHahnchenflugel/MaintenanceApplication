# app/routes/web/dashboard.py

from flask import render_template

from templates.db import query_one
from templates.helpers import human_delta_to_now
from . import web_bp


@bp.get("/", strict_slashes=False)
@bp.get("/dashboard", strict_slashes=False)
def dashboard():
    # Total open / in-progress issues
    num_open_issues_sql = query_one(
        """
        SELECT
            COUNT(*)
        FROM issue
        WHERE status_id IN (
            SELECT id
            FROM issue_status
            WHERE code IN ('OPEN', 'IN_PROGRESS')
        );
        """
    )

    # Total blocked issues
    num_blocked_issues_sql = query_one(
        """
        SELECT
            COUNT(*)
        FROM issue
        WHERE status_id IN (
            SELECT id
            FROM issue_status
            WHERE code = 'BLOCKED'
        );
        """
    )

    # Oldest open / in-progress issue
    oldest_issue_sql = query_one(
        """
        SELECT 
            id, created_at
        FROM issue
        WHERE status_id IN (
            SELECT id
            FROM issue_status
            WHERE code IN ('OPEN', 'IN_PROGRESS')
        ) 
        ORDER BY created_at ASC
        LIMIT 1;
        """
    )

    issue_info = {
        "num_open_issues": num_open_issues_sql[0] if num_open_issues_sql else 0,
        "num_blocked_issues": num_blocked_issues_sql[0] if num_blocked_issues_sql else 0,
        "oldest_issue": None,
    }

    if oldest_issue_sql:
        issue_info["oldest_issue"] = {
            "id": oldest_issue_sql[0],
            "age": human_delta_to_now(oldest_issue_sql[1]),
        }

    return render_template("dashboard/index.html", issue_info=issue_info)
