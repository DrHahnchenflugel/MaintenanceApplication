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
            "reported_by": r["reported_by"],  # string or None
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "closed_at": r["closed_at"],
            "last_action_at": r["last_action_at"],
            "last_action_type": r["last_action_type_code"],
        })

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": items,
    }

def get_issue(issue_id: str):
    """
    Return a single issue with its actions, or None if not found.
    """
    r = issue_db.get_issue_row(issue_id)
    if r is None:
        return None

    # Fetch actions timeline
    action_rows = issue_db.list_issue_actions(issue_id)
    actions = []
    for a in action_rows:
        actions.append({
            "id": a["id"],
            "type": {
                "id": a["action_type_id"],
                "code": a["action_type_code"],
                "label": a["action_type_label"],
            },
            "body": a["body"],
            "created_at": a["created_at"],
            "created_by": {
                "id": a["created_by"],
                "name": str(a["created_by"]),  # placeholder until user table
            },
        })

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
        "reported_by": r["reported_by"],
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
        "closed_at": r["closed_at"],
        "last_action_at": r["last_action_at"],
        "last_action_type": r["last_action_type_code"],
        "last_action_type_label": r["last_action_type_label"],
        "actions": actions,
    }

def create_issue(data: dict):
    """
    Create a new issue, initial action, and status history.

    Expected keys in data:
      - asset_id       (UUID string, required)
      - title          (str, required)
      - description    (str, required)
      - reported_by    (UUID string, required)
      - created_by     (UUID string, required)
      - status_id      (UUID string, optional; default = 'OPEN' status)
    """

    asset_id = data.get("asset_id")
    title = data.get("title")
    description = data.get("description")
    reported_by = data.get("reported_by")
    created_by = data.get("created_by")
    status_id = data.get("status_id")

    # Basic sanity; real validation should live in route or a schema layer
    if not asset_id or not title or not description or not created_by:
        raise ValueError("Missing required fields for issue creation")

    # Default status: code 'OPEN' if status_id not provided
    if not status_id:
        status_id = issue_db.get_issue_status_id_by_code("OPEN")
        if not status_id:
            raise RuntimeError("No issue_status row with code 'OPEN' found")

    # 1) Create the issue itself
    issue_row = issue_db.create_issue_row(
        asset_id=asset_id,
        status_id=status_id,
        title=title,
        description=description,
        reported_by=reported_by,
    )

    issue_id = issue_row["id"]

    # 2) Initial status history: from NULL -> status_id
    issue_db.create_issue_status_history_row(
        issue_id=issue_id,
        from_status_id=status_id,
        to_status_id=status_id,
        changed_by=created_by,
    )

    # 3) Initial action: type 'created'
    created_type_id = issue_db.get_action_type_id_by_code("CREATED")
    if not created_type_id:
        raise RuntimeError("No action_type row with code 'CREATED' found")

    issue_db.create_issue_action_row(
        issue_id=issue_id,
        action_type_id=created_type_id,
        body=data.get("initial_action_body") or "Issue created",
        created_by=created_by,
    )

    # You can either return full issue or just ID
    return {
        "id": issue_id,
    }
