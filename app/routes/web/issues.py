from flask import render_template, url_for
from . import bp as web_bp

@web_bp.get("/issues", strict_slashes=False)
def issues_index():
    """
    Render the issues page shell. The actual data comes from the v2 API.
    """
    api_issues_url = url_for("api_v2.list_issues")

    return render_template(
        "issues/viewIssues.html",
        api_issues_url=api_issues_url,
    )


pass