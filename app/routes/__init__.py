from .api import bp as api_root_bp
from .api.v2 import bp as api_v2_bp
from .web import bp as web_bp

def format_dt(dt):
    if not dt:
        return ""
    return dt.strftime("%H:%M"), dt.strftime("%d-%m-%Y")


app.jinja_env.filters["format_dt"] = format_dt

def register_blueprints(app):
    app.register_blueprint(api_root_bp)  # /maintenance/api/
    app.register_blueprint(api_v2_bp)    # /maintenance/api/v2/...
    app.register_blueprint(web_bp)       # /maintenance/...