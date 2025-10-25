from .web import bp as web_bp
from .api.v2 import bp as api_v2_bp

def register_blueprints(app):
    app.register_blueprint(web_bp)
    app.register_blueprint(api_v2_bp) # API v2
    # keep , url_prefix="/maintenance" in both register_blueprint()s?