from flask import Blueprint

# This is the v2 API blueprint
bp = Blueprint("api_v2", __name__, url_prefix="/maintenance/api/v2")
# or "/api/v2" if that’s what you want

# Import modules so they register routes on this blueprint
from . import asset, issues  # noqa: F401
