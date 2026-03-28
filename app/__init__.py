import os
from flask import Flask, request
from .routes import register_blueprints
from .health import health_bp
from .services import sites as site_service
from pillow_heif import register_heif_opener
register_heif_opener()


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
            return ["",""]
        return dt.strftime("%H:%M"), dt.strftime("%d-%m-%Y")

    app.jinja_env.filters["format_dt"] = format_dt

    @app.context_processor
    def inject_site_context():
        preferred_site_return_to = request.full_path
        if request.method != "GET":
            preferred_site_return_to = request.referrer or request.full_path

        return {
            "available_sites": site_service.list_sites(),
            "current_site": site_service.get_current_site(),
            "preferred_site_return_to": preferred_site_return_to,
        }

    register_blueprints(app)
    app.register_blueprint(health_bp, url_prefix="/maintenance")
    app.secret_key = os.environ["FLASK_SECRET"]

    app.config.update(
        {
            "ATTACHMENT_ROOT": os.environ.get("ATTACHMENT_ROOT", "/tmp/attachments"),
            "MAINTENANCE_PUBLIC_BASE_URL": os.environ.get("MAINTENANCE_PUBLIC_BASE_URL", "http://server2-ubuntu"),
        }
    )

    return app
