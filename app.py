from service_event_checker import create_app
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import logging

# Create the Flask application instance
app = create_app()
app.logger.setLevel(logging.DEBUG)
# Apply ProxyFix for reverse proxy setups (like Azure Web Apps)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

if __name__ == "__main__":
    # Retrieve the port from environment variables (required by Azure Web App)
    port = int(os.getenv('PORT', 8000))
    
    # Run the Flask app with the correct host and port
    app.run(host="0.0.0.0", port=port)
