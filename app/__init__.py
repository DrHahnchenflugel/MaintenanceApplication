import os
from flask import Flask
from .routes import register_blueprints

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
    app.secret_key = os.environ["FLASK_SECRET"]
    app.register_blueprint(app)

    app.config.update(
        {
            "ATTACHMENT_ROOT": os.environ.get("ATTACHMENT_ROOT", "/tmp/attachments")
        }
    )

    return app
