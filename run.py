# Load environment vars from /app/.env
from dotenv import load_dotenv
load_dotenv()

# Initialise the app
from app import initialise_application
maintenance_app = initialise_application()

if __name__ == "main":
    maintenance_app.run(host="0.0.0.0", port=5001, debug=True) # TODO: remove debug=True when putting into prod
