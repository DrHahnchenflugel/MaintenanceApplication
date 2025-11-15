import os
from flask import Flask
from .routes import register_blueprints
from .health import health_bp

def initialise_application():
    # Load environment vars from /app/.env
    from dotenv import load_dotenv
    load_dotenv()
    app = Flask(
        __name__,
        template_folder = "templates",
        static_folder = "static",
        static_url_path = "/maintenance/static"
    )
    register_blueprints(app)
    app.register_blueprint(health_bp, url_prefix="/maintenance")
    app.secret_key = os.environ["FLASK_SECRET"]

    app.config.update(
        {
            "ATTACHMENT_ROOT": os.environ.get("ATTACHMENT_ROOT", "/tmp/attachments")
        }
    )

    return app
