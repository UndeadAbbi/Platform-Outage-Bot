import logging
import requests
import os
from dotenv import load_dotenv
from service_event_checker.event_tracker import EventTracker 
from service_event_checker.config import get_test_mode, init_env_variables

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

# Initialize tracked events
if testMode:
    tracked_events = {
        "test-event-12891": {
            "id": "test-event-12891",
            "IncidentImpacts": [
                {
                    "type": "Service Disruption",
                    "severity": "Critical",
                    "startTime": "2024-09-10T12:00:00Z"
                }
            ],
            "IncidentEvents": [
                {
                    "type": "investigatingCauseOfIssue",
                    "message": "We are currently investigating the cause of the issue."
                }
            ],
            "affectsAll": False
        }
    }
else:
    tracked_events = {}  # Placeholder, to be handled with Azure Table Storage in production

# Initialize the Event Tracker
event_tracker = EventTracker(test_mode=testMode)

class SalesforceServiceChecker:
    @staticmethod
    def check_service():
        logger.debug("Checking Salesforce service incidents...")
        fetch_salesforce_incidents()

def fetch_salesforce_incidents():
    """
    Fetches Salesforce incidents from the API.
    In test mode, simulated incidents are used.
    """
    if testMode:
        logger.debug("Simulating Salesforce incidents in test mode.")
        for incident_id, incident_data in tracked_events.items():
            process_incident(incident_data)
    else:
        url = "https://status.salesforce.com/api/incidents/active"
        headers = {
            "Accept": "application/json"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            incidents = response.json()

            if not incidents:
                logger.info("No incidents found on Salesforce status page.")
                return

            for incident in incidents:
                process_incident(incident)

            # Process tracked events separately
            for event_id in tracked_events.copy():
                fetch_and_process_tracked_event(event_id)

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Salesforce incidents: {e}")

def fetch_and_process_tracked_event(event_id):
    """
    Fetches and processes individual tracked events.
    """
    if testMode:
        logger.debug(f"Processing simulated tracked event: {event_id}")
        if event_id in tracked_events:
            process_incident(tracked_events[event_id])
    else:
        url = f"https://status.salesforce.com/api/incidents/{event_id}"
        headers = {
            "Accept": "application/json"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            incident = response.json()
            process_incident(incident)

            # If the event is resolved, remove it from the tracked events list
            if any(event['type'] == 'resolution' or event['type'] == 'resolved' for event in incident.get('IncidentEvents', [])):
                tracked_events.pop(event_id)

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching tracked Salesforce incident {event_id}: {e}")

def process_incident(incident):
    """
    Processes and logs individual incidents.
    """
    platform = "Salesforce"
    event_name = f"{incident['id']} {incident['IncidentImpacts'][0]['type']} {incident['IncidentImpacts'][0]['severity']}"
    status = "Ongoing" if all(event['type'] != 'resolution' and event['type'] != 'resolved' for event in incident['IncidentEvents']) else "Resolved"
    impact_start_time = incident['IncidentImpacts'][0].get('startTime', 'N/A')
    affects_all = incident.get('affectsAll', False)

    # Map description to IncidentEvents.message when the type is "investigatingCauseOfIssue"
    description = "None"
    for event in incident.get('IncidentEvents', []):
        if event['type'] == 'investigatingCauseOfIssue':
            description = event.get('message', 'No description available.')
            break

    # Log the event with the Event Tracker
    event_data = {
        "platform": platform,
        "event_name": event_name,
        "status": status,
        "impact_start_time": impact_start_time,
        "description": description
    }

    internal_id = event_tracker.log_event(event_data)

    # Construct the message
    message = (
        f"**Platform:** {platform}\n"
        f"**Event Name:** {event_name}\n"
        f"**Status:** {status}\n"
        f"**Impact Start Time:** {impact_start_time}\n"
        f"**Affects All?:** {affects_all}\n"
        f"**Description:** {description}\n"
        f"**Internal ID:** {internal_id}\n"
    )

    # Log the event
    logger.info(f"Service health event data:\n{message}")

if __name__ == "__main__":
    SalesforceServiceChecker.check_service()
