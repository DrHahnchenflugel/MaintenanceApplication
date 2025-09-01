import os
from flask import Flask
from .routes import bp

def initialise_application():
    app = Flask(__name__)
    app.secret_key = "tbd"
    app.register_blueprint(bp)

    app.config.update(
        {
            "ATTACHMENT_ROOT": os.environ.get("ATTACHMENT_ROOT", "/tmp/attachments")
        }
    )

    return app
