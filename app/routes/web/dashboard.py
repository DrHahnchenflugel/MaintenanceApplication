from flask import render_template, url_for
from . import web_bp


@web_bp.get("/", strict_slashes=False)
@web_bp.get("/dashboard", strict_slashes=False)
def dashboard():
    # Use url_for so you don’t hardcode the path
    api_issue_summary_url = url_for("api_v2.issues_summary")

    return render_template(
        "dashboard/index.html",
        api_issue_summary_url=api_issue_summary_url,
    )
