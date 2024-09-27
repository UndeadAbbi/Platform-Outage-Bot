from service_event_checker.config import get_test_mode, init_env_variables
import logging
import requests
import os
from datetime import datetime
from service_event_checker.event_tracker import EventTracker  # Import the Event Tracker

# Initialize environment variables
init_env_variables()

# Dynamically retrieve the test mode state
testMode = get_test_mode()

# Configure logging based on test mode
if testMode:
    logging.basicConfig(level=logging.DEBUG)  # Debug level logging in test mode
else:
    logging.basicConfig(level=logging.INFO)  # Info level logging in production

logger = logging.getLogger(__name__)

# Initialize the Event Tracker
event_tracker = EventTracker(test_mode=testMode)

class GithubServiceChecker:
    @staticmethod
    def check_service():
        fetch_github_incidents()

def fetch_github_incidents():
    """
    Fetch unresolved incidents from GitHub's status API.
    In test mode, simulate the data.
    """
    if testMode:
        # Simulated test data
        incidents = [
            {
                'id': 'test-incident-1',
                'name': 'Test Incident: GitHub Actions Outage',
                'impact': 'critical',
                'status': 'investigating',
                'shortlink': 'https://stspg.io/test-incident',
                'created_at': '2024-09-10T12:00:00Z'
            }
        ]
        for incident in incidents:
            process_incident(incident)
        clean_up_resolved_incidents(incidents)
    else:
        # Real data fetching in production
        url = "https://www.githubstatus.com/api/v2/incidents/unresolved.json"
        headers = {'Accept': 'application/json'}

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            incidents = response.json().get("incidents", [])

            if not incidents:
                logger.info("No unresolved incidents found on GitHub status page.")
                clean_up_resolved_incidents([])
            else:
                for incident in incidents:
                    process_incident(incident)
                clean_up_resolved_incidents(incidents)

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching GitHub incidents: {e}")

def process_incident(incident):
    """
    Process individual incident and log it if it's not already tracked.
    """
    incident_id = incident['id']
    event_name = incident['name']
    severity = incident['impact']
    status = incident['status']
    link = incident['shortlink']
    impact_start_time = incident['created_at']

    # Track the incident
    event_data = {
        "platform": "Github",
        "event_name": event_name,
        "severity": severity,
        "status": status,
        "link": link,
        "impact_start_time": impact_start_time
    }

    # Log the event and get its Internal ID
    internal_id = event_tracker.log_event(event_data)

    # Construct the message with the Internal ID
    output_incident(internal_id, event_name, severity, status, link, impact_start_time)

def clean_up_resolved_incidents(current_incidents):
    """
    Clean up resolved incidents and log their resolution.
    """
    current_ids = [incident['id'] for incident in current_incidents]
    resolved_ids = [incident_id for incident_id in event_tracker.list_tracked_events() if incident_id not in current_ids]

    for incident_id in resolved_ids:
        incident = event_tracker.get_event_by_id(incident_id)
        output_incident(incident_id, incident["event_name"], incident["severity"], "Resolved", incident["link"], incident["impact_start_time"])
        event_tracker.resolve_event(incident_id)

def output_incident(internal_id, event_name, severity, status, link, impact_start_time):
    """
    Output the incident details in a structured format.
    """
    platform = "Github"
    message = (
        f"**Platform:** {platform}\n"
        f"**Event Name:** {event_name}\n"
        f"**Severity:** {severity}\n"
        f"**Status:** {status}\n"
        f"**Link:** {link}\n"
        f"**Impact Start Time:** {impact_start_time}\n"
        f"**Internal ID:** {internal_id}\n"
    )

    # Log the incident (or send to Slack, etc.)
    logger.warning(f"Service health incident data:\n{message}")

if __name__ == "__main__":
    GithubServiceChecker.check_service()
