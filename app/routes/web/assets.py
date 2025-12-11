from flask import render_template, url_for
from . import bp as web_bp

@web_bp.get("/assets", strict_slashes=False)
def assets_index():
    """
    Render the assets page shell. The actual data comes from the v2 API.
    """
    api_assets_url = url_for("api_v2.list_assets")

    return render_template(
        "assets/viewAssets.html",
        api_assets_url=api_assets_url,
    )
