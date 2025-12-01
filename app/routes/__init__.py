from .api import bp as api_root_bp
from .api.v2 import bp as api_v2_bp

def register_blueprints(app):
    app.register_blueprint(api_root_bp)  # /maintenance/api/
    app.register_blueprint(api_v2_bp)    # /maintenance/api/v2/...