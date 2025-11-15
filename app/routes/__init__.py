from .web import web_bp as web_bp
from .api.v2 import bp as api_v2_bp

def register_blueprints(app):
    app.register_blueprint(web_bp, url_prefix="/maintenance")
    app.register_blueprint(api_v2_bp, url_prefix="/maintenance/api/v2") # API v2