import logging
import os
from flask import Flask
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from service_event_checker.config import init_env_variables  # Import environment initialization
import json

def create_app():
    app = Flask(__name__)

    # Initialize environment variables (if you are using .env file)
    init_env_variables()

    # Load config from JSON file
    load_config(app)

    # Configure logging
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/service_event_checker.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('Service Event Checker startup')

    # Import and register blueprints
    from service_event_checker.routes import bp as routes_bp
    app.register_blueprint(routes_bp)

    # Initialize other components, such as the scheduler
    from service_event_checker.tasks import initialize_scheduler
    initialize_scheduler(app)

    return app

def load_config(app):
    # Load config.json into Flask app config
    config_path = 'config.json'
    if os.path.exists(config_path):
        with open(config_path) as config_file:
            config_data = json.load(config_file)
            app.config.update(config_data)
    else:
        app.logger.error(f"Configuration file {config_path} not found")
