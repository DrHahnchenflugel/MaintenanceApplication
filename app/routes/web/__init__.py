from flask import Blueprint
bp = Blueprint("app", __name__, url_prefix="/maintenance")

# Import route modules, so they attach to bp
from . import dashboard     # noqa: F401
from . import issues        # noqa: F401
from . import files         # noqa: F401
from . import assets        # noqa: F401
