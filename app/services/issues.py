from app.db import issues as issue_db

def list_issues(page: int, page_size: int, filters: dict):
    offset = (page - 1) * page_size
    closed_mode = "open"

    closed = filters.get("closed")
    if isinstance(closed, str):
        v = closed.lower()
        if v == "true":
            closed_mode = "closed"
        elif v == "false":
            closed_mode = "open"
        elif v == "all":
            closed_mode = "all"

    search = filters.get("search")
    if search == "":
        search = None

    rows, total = issue_db.list_issue_rows(
        site_id=filters.get("site_id"),
        asset_id=filters.get("asset_id"),
        status_id=filters.get("status_id"),
        reported_by=filters.get("reported_by"),
        created_from=filters.get("created_from"),
        created_to=filters.get("created_to"),
        closed_mode=closed_mode,
        search=search,
        sort=[("created_at", "desc")],
        limit=page_size,
        offset=offset,
    )

    items = []
    for r in rows:
        items.append({
            "id": r["id"],
            "title": r["title"],
            "status": {
                "id": r["status_id"],
                "code": r["status_code"],
                "label": r["status_label"],
            },
            "asset": {
                "id": r["asset_id"],
                "asset_tag": r["asset_tag"],
                "site_id": r["site_id"],
            },
            "reported_by": {
                "id": r["reported_by"],
                "name": str(r["reported_by"]),  # placeholder
            },
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "closed_at": r["closed_at"],
            "last_action_at": r["last_action_at"],
            "last_action_type": r["last_action_type_code"],
            "last_action_type_label": r["last_action_type_label"],
        })

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": items,
    }

def get_issue(issue_id: str):
    """
    Return a single issue as a JSON-ready dict, or None if not found.
    """
    r = issue_db.get_issue_row(issue_id)
    if r is None:
        return None

    return {
        "id": r["id"],
        "title": r["title"],
        "description": r["description"],
        "status": {
            "id": r["status_id"],
            "code": r["status_code"],
            "label": r["status_label"],
        },
        "asset": {
            "id": r["asset_id"],
            "asset_tag": r["asset_tag"],
            "site_id": r["site_id"],
        },
        "reported_by": {
            "id": r["reported_by"],
            "name": str(r["reported_by"]),  # placeholder until you have users
        },
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
        "closed_at": r["closed_at"],
        "last_action_at": r["last_action_at"],
        "last_action_type": r["last_action_type_code"],
        # optional if you want it:
        # "last_action_type_label": r["last_action_type_label"],
    }
