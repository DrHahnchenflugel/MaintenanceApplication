import os
from flask import Flask
from .routes import register_blueprints
from .health import health_bp

def initialise_application():
    from dotenv import load_dotenv
    load_dotenv()
    app = Flask(
        __name__,
        template_folder = "templates",
        static_folder = "static",
        static_url_path = "/maintenance/static"
    )

    def format_dt(dt):
        if not dt:
            return ""
        return dt.strftime("%H:%M"), dt.strftime("%d-%m-%Y")

    app.jinja_env.filters["format_dt"] = format_dt

    register_blueprints(app)
    app.register_blueprint(health_bp, url_prefix="/maintenance")
    app.secret_key = os.environ["FLASK_SECRET"]

    app.config.update(
        {
            "ATTACHMENT_ROOT": os.environ.get("ATTACHMENT_ROOT", "/tmp/attachments")
        }
    )

    return app
