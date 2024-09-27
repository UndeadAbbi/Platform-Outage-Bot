import logging
import requests
from dotenv import load_dotenv
from service_event_checker.event_tracker import EventTracker  # Import the Event Tracker
from service_event_checker.config import get_test_mode, init_env_variables
import os

# Initialize environment variables
init_env_variables()

# Dynamically retrieve the test mode state
testMode = get_test_mode()

# Configure logging based on testMode
if testMode:
    logging.basicConfig(level=logging.DEBUG)  # Debug level logging in test mode
else:
    logging.basicConfig(level=logging.INFO)  # Info level logging in production

logger = logging.getLogger(__name__)

# Initialize the Event Tracker
event_tracker = EventTracker(test_mode=testMode)

class SlackServiceChecker:
    @staticmethod
    def check_service():
        logger.debug("Checking Slack service status...")
        fetch_slack_status()

def fetch_slack_status():
    """
    Fetch the current status from the Slack status API.
    In test mode, simulate the status.
    """
    if testMode:
        logger.debug("Simulating Slack status in test mode.")
        simulated_data = {
            "status": "active",
            "active_incidents": [
                {
                    "id": 1234,
                    "title": "Test Slack Incident",
                    "status": "active",
                    "url": "https://status.slack.com/incidents/1234",
                    "date_created": "2024-09-10T12:00:00Z",
                    "notes": [
                        {
                            "body": "We are currently investigating an issue with Slack.",
                            "date_created": "2024-09-10T12:00:00Z"
                        }
                    ]
                }
            ]
        }
        process_slack_incidents(simulated_data["active_incidents"])
    else:
        url = "https://slack-status.com/api/v2.0.0/current"
        headers = {
            'Accept': 'application/json'
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            # Process active incidents if any
            active_incidents = data.get("active_incidents", [])
            if active_incidents:
                process_slack_incidents(active_incidents)
            else:
                logger.info("No active incidents found on Slack status page.")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Slack status: {e}")

def process_slack_incidents(incidents):
    """
    Process the list of active incidents and log the output.
    """
    for incident in incidents:
        event_name = incident.get("title", "N/A")
        status = incident.get("status", "N/A")
        link = incident.get("url", "N/A")
        impact_start_time = incident.get("date_created", "N/A")
        notes = incident.get("notes", [])
        description = "\n".join([note.get("body", "") for note in notes])

        # Log the event with the Event Tracker
        event_data = {
            "platform": "Slack",
            "event_name": event_name,
            "status": status,
            "impact_start_time": impact_start_time,
            "description": description
        }

        # Generate Internal ID using the Event Tracker
        internal_id = event_tracker.log_event(event_data)

        # Construct the message with the Internal ID
        message = (
            f"**Platform:** Slack\n"
            f"**Event Name:** {event_name}\n"
            f"**Status:** {status}\n"
            f"**Link:** {link}\n"
            f"**Impact Start Time:** {impact_start_time}\n"
            f"**Description:** {description}\n"
            f"**Internal ID:** {internal_id}\n"
        )

        # Log the incident
        logger.info(f"Service health incident data:\n{message}")

if __name__ == "__main__":
    SlackServiceChecker.check_service()
