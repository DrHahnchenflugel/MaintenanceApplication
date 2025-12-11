# app/routes/api/v2/issues.py

from flask import jsonify
from . import bp
from app.services.issues import (
    count_issues_by_status_codes,
    get_oldest_issue_by_status_codes,
)
from app.helpers import human_delta_to_now


@bp.route("/issues/summary", methods=["GET"])
def issues_summary():
    open_like_statuses = ("OPEN", "IN_PROGRESS")
    blocked_statuses = ("BLOCKED",)

    num_open_issues = count_issues_by_status_codes(open_like_statuses)
    num_blocked_issues = count_issues_by_status_codes(blocked_statuses)
    oldest_issue = get_oldest_issue_by_status_codes(open_like_statuses)

    oldest_issue_payload = None
    if oldest_issue is not None:
        issue_id, created_at = oldest_issue
        oldest_issue_payload = {
            "id": issue_id,
            "age": human_delta_to_now(created_at),
        }

    return jsonify({
        "num_open_issues": num_open_issues,
        "num_blocked_issues": num_blocked_issues,
        "oldest_issue": oldest_issue_payload,
    }), 200
