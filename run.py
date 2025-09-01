# Initialise the app
from app import initialise_application
maintenance_app = initialise_application()

maintenance_app.run(host="0.0.0.0", port=5001, debug=True) # TODO: remove debug=True when putting into prod
