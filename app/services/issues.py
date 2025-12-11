from app.db import issues as issues_repo

def count_issues_by_status_codes(status_codes):
    """
    Service-level wrapper for counting issues by status codes.

    status_codes: iterable of strings, e.g. ("OPEN", "IN_PROGRESS")
    Returns: int
    """
    if not status_codes:
        return 0

    # Normalise to a simple list of strings
    codes = [str(code) for code in status_codes]

    return issues_repo.count_issues_by_status_codes_row(codes)

def get_oldest_issue_by_status_codes(status_codes):
    """
    Service-level wrapper for getting oldest issue by status codes.

    status_codes: iterable of strings, e.g. ("OPEN", "IN_PROGRESS")
    Returns:
        (issue_id, created_at) tuple or None
    """
    if not status_codes:
        return None

    codes = [str(code) for code in status_codes]

    row = issues_repo.get_oldest_issue_by_status_codes_row(codes)
    if row is None:
        return None

    return (row["id"], row["created_at"])
