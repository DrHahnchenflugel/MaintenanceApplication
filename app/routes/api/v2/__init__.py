from flask import Blueprint
bp = Blueprint("api_v2", __name__, url_prefix="/api/v2")

# pull in endpoints
from . import taxonomy      # noqa: F401