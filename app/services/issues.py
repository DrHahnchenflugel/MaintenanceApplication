import os
from werkzeug.utils import secure_filename
from flask import current_app
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
                "name": str(a["created_by"] or "-"),  # TODO: not sure if i like this
            },
        })

    # Status history
    hist_rows = issue_db.list_issue_status_history(issue_id)
    status_history = []
    for h in hist_rows:
        status_history.append({
            "id": h["id"],
            "from_status": None if h["from_status_id"] is None else {
                "id": h["from_status_id"],
                "code": h["from_status_code"],
                "label": h["from_status_label"],
            },
            "to_status": {
                "id": h["to_status_id"],
                "code": h["to_status_code"],
                "label": h["to_status_label"],
            },
            "changed_at": h["changed_at"],
            "changed_by": h["changed_by"] or "-",
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
        "status_history": status_history,
    }

def create_issue(data: dict):
    """
    Create a new issue, initial action, and status history.

    data:
      - asset_id    (UUID string, required)
      - title       (str, required)
      - description (str, required)
      - reported_by (str, optional)
      - created_by  (str, optional, default "-")
      - status_id   (UUID string, optional; default status 'OPEN')
    """

    asset_id = data.get("asset_id")
    title = data.get("title")
    description = data.get("description")
    reported_by = data.get("reported_by")
    created_by = data.get("created_by") or "-"  # default here
    status_id = data.get("status_id")

    if not asset_id or not title or not description:
        raise ValueError("Missing required fields for issue creation")

    if not status_id:
        status_id = issue_db.get_issue_status_id_by_code("OPEN")
        if not status_id:
            raise RuntimeError("No issue_status row with code 'OPEN' found")

    # 1) issue row
    issue_row = issue_db.create_issue_row(
        asset_id=asset_id,
        status_id=status_id,
        title=title,
        description=description,
        reported_by=reported_by,
    )
    issue_id = issue_row["id"]

    # 2) status history (NULL -> OPEN)
    issue_db.create_issue_status_history_row(
        issue_id=issue_id,
        from_status_id=None,
        to_status_id=status_id,
        changed_by=created_by,  # string
    )

    # 3) initial action (CREATED)
    created_type_id = issue_db.get_action_type_id_by_code("CREATED")
    if not created_type_id:
        raise RuntimeError("No action_type row with code 'CREATED' found")

    initial_body = data.get("initial_action_body") or "Issue created"

    issue_db.create_issue_action_row(
        issue_id=issue_id,
        action_type_id=created_type_id,
        body=initial_body,
        created_by=created_by,  # string
    )

    return {"id": issue_id}

def add_issue_action(issue_id: str, data: dict):
    """
    Add an action to an issue, optionally changing status.

    data:
      - action_type_code (str, required; one of CREATED, NOTE, INSPECT, REPAIR, CLOSED)
      - body             (str, required)
      - created_by       (str, optional, default "-")
      - new_status_id    (UUID string, optional)
    """

    action_type_code = data.get("action_type_code")
    body = data.get("body")
    created_by = data.get("created_by") or "-"
    new_status_id = data.get("new_status_id")

    if not action_type_code or not body:
        raise ValueError("Missing required fields for issue action")

    # confirm issue exists + get current status
    current_status_id = issue_db.get_issue_status_id(issue_id)
    if current_status_id is None:
        return None  # route will turn into 404

    # look up action_type.id by code
    action_type_id = issue_db.get_action_type_id_by_code(action_type_code)
    if not action_type_id:
        raise ValueError(f"Unknown action_type_code: {action_type_code}")

    # 1) insert action
    issue_db.create_issue_action_row(
        issue_id=issue_id,
        action_type_id=action_type_id,
        body=body,
        created_by=created_by,
    )

    # 2) optional status change
    if new_status_id and new_status_id != str(current_status_id):
        issue_db.create_issue_status_history_row(
            issue_id=issue_id,
            from_status_id=current_status_id,
            to_status_id=new_status_id,
            changed_by=created_by,
        )

        issue_db.update_issue_row(
            issue_id,
            {"status_id": new_status_id},
        )

    return {"issue_id": issue_id}

def update_issue(issue_id: str, data: dict):
    """
    Partially update an issue. Does NOT change status.
    Allowed fields:
      - title
      - description
      - reported_by
      - asset_id
    """

    fields = {}

    if "title" in data and data["title"] is not None:
        fields["title"] = data["title"]

    if "description" in data and data["description"] is not None:
        fields["description"] = data["description"]

    if "reported_by" in data and data["reported_by"] is not None:
        fields["reported_by"] = data["reported_by"]

    if "asset_id" in data and data["asset_id"] is not None:
        fields["asset_id"] = data["asset_id"]

    if not fields:
        # nothing to do; just return current issue
        return get_issue(issue_id)

    updated = issue_db.update_issue_row(issue_id, fields)
    if updated is None:
        return None

    # Return full issue view (with actions/history)
    return get_issue(issue_id)

def list_issue_statuses():
    rows = issue_db.list_issue_status_rows()
    return [
        {
            "id": r["id"],
            "code": r["code"],
            "label": r["label"],
            "display_order": r["display_order"],
        }
        for r in rows
    ]

def list_action_types():
    rows = issue_db.list_action_type_rows()
    return [
        {
            "id": r["id"],
            "code": r["code"],
            "label": r["label"],
            "display_order": r["display_order"],
        }
        for r in rows
    ]

def create_issue_status(data: dict):
    code = (data.get("code") or "").strip().upper()
    label = (data.get("label") or "").strip()
    display_order = data.get("display_order")

    if not code or not label:
        raise ValueError("code and label are required for issue_status")

    if display_order is None:
        raise ValueError("display_order is required and must be an integer")

    row = issue_db.create_issue_status_row(code, label, display_order)
    return {
        "id": row["id"],
        "code": row["code"],
        "label": row["label"],
        "display_order": row["display_order"],
    }

def create_action_type(data: dict):
    code = (data.get("code") or "").strip().upper()
    label = (data.get("label") or "").strip()
    display_order = data.get("display_order")

    if not code or not label:
        raise ValueError("code and label are required for action_type")

    if display_order is None:
        raise ValueError("display_order is required and must be an integer")

    row = issue_db.create_action_type_row(code, label, display_order)
    return {
        "id": row["id"],
        "code": row["code"],
        "label": row["label"],
        "display_order": row["display_order"],
    }

def get_issue_attachment(issue_id: str):
    """
    Return attachment metadata for an issue, or None.
    Expected keys: filepath, content_type
    """
    return issues_db.get_issue_attachment_by_issue_id(issue_id)

def add_issue_attachment(issue_id: str, file):
    if file is None or file.filename == "":
        raise ValueError("No file provided")

    # MIME type from Werkzeug (browser-provided but still useful)
    content_type = file.mimetype
    if not content_type:
        raise ValueError("Missing content type")

    # Pull allowed types from DB
    allowed_types = issues_db.list_accepted_attachment_content_types()
    if content_type not in allowed_types:
        raise ValueError(f"Unsupported content type: {content_type}")

    # Enforce 1 attachment per issue
    existing = issues_db.get_issue_attachment_by_issue_id(issue_id)
    if existing:
        raise ValueError("Issue already has an attachment")

    # Use filename ONLY to infer extension for storage
    filename = secure_filename(file.filename)
    if "." not in filename:
        raise ValueError("File must have an extension")

    ext = filename.rsplit(".", 1)[1].lower()

    root = current_app.config["ATTACHMENT_ROOT"]

    # Storage layout: issues/<issue_id>/attachment.<ext>
    rel_dir = f"issues/{issue_id}"
    abs_dir = os.path.join(root, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)

    rel_path = f"{rel_dir}/attachment.{ext}"
    abs_path = os.path.join(root, rel_path)

    file.save(abs_path)

    return issues_db.create_issue_attachment(
        issue_id=issue_id,
        filepath=rel_path,
        content_type=content_type,
    )

def list_accepted_attachment_content_types():
    return issues_db.list_accepted_attachment_content_types()

def create_accepted_attachment_content_type(data: dict):
    content_type = (data.get("content_type") or "").strip().lower()

    if not content_type:
        raise ValueError("Missing content_type")

    if "/" not in content_type:
        raise ValueError("Invalid MIME type format")

    return issues_db.create_accepted_attachment_content_type(content_type)

def delete_accepted_attachment_content_type(content_type: str):
    ok = issues_db.delete_accepted_attachment_content_type(content_type)
    if not ok:
        raise ValueError("Content type not found")
