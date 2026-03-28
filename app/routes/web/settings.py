from flask import render_template

from . import bp as web_bp


@web_bp.get("/settings", strict_slashes=False)
def settings():
    return render_template("settings/index.html")
