from flask import render_template, url_for

from . import bp as web_bp


@web_bp.get("/", strict_slashes=False)
@web_bp.get("/dashboard", strict_slashes=False)
def dashboard():
    return render_template(
        "dashboard/index.html",
        api_dashboard_url=url_for("api_v2.dashboard_data"),
    )
