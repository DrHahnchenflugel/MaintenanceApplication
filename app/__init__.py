import os
from flask import Flask
from .routes import bp

# Load environment vars from /app/.env
from dotenv import load_dotenv
load_dotenv()

def initialise_application():
    app = Flask(__name__)
    app.secret_key = os.environ["FLASK_SECRET"]
    app.register_blueprint(bp)

    app.config.update(
        {
            "ATTACHMENT_ROOT": os.environ.get("ATTACHMENT_ROOT", "/tmp/attachments")
        }
    )

    return app
