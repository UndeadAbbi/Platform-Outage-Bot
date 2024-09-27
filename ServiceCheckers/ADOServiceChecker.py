from service_event_checker.config import get_test_mode, init_env_variables
import logging
from service_event_checker.event_tracker import EventTracker
import requests
from datetime import datetime
import os

# Initialize environment variables
init_env_variables()

# Dynamically retrieve the test mode state
testMode = get_test_mode()

# Initialize the Event Tracker
event_tracker = EventTracker(test_mode=testMode)

# Configure logging based on test mode
if testMode:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

class ADOServiceChecker:
    @staticmethod
    def check_service():
        service_data = fetch_service_status()
        if service_data:
            process_service_status(service_data)

def fetch_service_status():
    """
    Fetches the Azure DevOps service health data from the status API.
    """
    if testMode:
        # Simulated service status data for testing
        return {
            "services": [
                {"id": "Core services", "geographies": [{"name": "United States", "health": "healthy"}]},
                {"id": "Boards", "geographies": [{"name": "United States", "health": "healthy"}]},
                {"id": "Pipelines", "geographies": [{"name": "United States", "health": "unhealthy"}]}  # Simulated unhealthy service
            ]
        }
    else:
        # Use environment variable URL for production
        BASE_URL = os.getenv("ADO_API_URL", "https://status.dev.azure.com/_apis/status/health?geographies=US&api-version=7.2-preview.1")
        headers = {
            "Accept": "application/json",
        }

        try:
            response = requests.get(BASE_URL, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Azure DevOps service status: {e}")
            return None

def process_service_status(data):
    """
    Processes the service status data and logs the event using EventTracker.
    """
    services = data.get('services', [])
    for service in services:
        service_name = service['id']
        geography = service['geographies'][0]
        health_status = geography['health']

        # Skip healthy services
        if health_status == 'healthy':
            continue

        # Create event data
        event_data = {
            "platform": "Azure DevOps",
            "event_name": service_name,
            "status": health_status,
            "impact_start_time": datetime.utcnow().strftime('%H:%M UTC %m/%d/%Y'),
            "description": f"{service_name} is currently {health_status}."
        }

        # Log the event and get its Internal ID
        internal_id = event_tracker.log_event(event_data)

        # Construct and log the event message
        message = (
            f"**Platform:** Azure DevOps\n"
            f"**Service Name:** {service_name}\n"
            f"**Impact Start Time:** {event_data['impact_start_time']}\n"
            f"**Status:** {health_status}\n"
            f"**Internal ID:** {internal_id}\n"
        )

        logger.warning(f"Service health event logged:\n{message}")

if __name__ == "__main__":
    checker = ADOServiceChecker()
    checker.check_service()
