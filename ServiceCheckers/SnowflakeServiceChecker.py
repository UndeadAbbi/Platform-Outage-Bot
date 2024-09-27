import logging
import requests
import html2text
import re
from dotenv import load_dotenv
from service_event_checker.event_tracker import EventTracker  # Import the Event Tracker
from service_event_checker.config import get_test_mode, init_env_variables

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

class SnowflakeServiceChecker:
    @staticmethod
    def check_service():
        logger.debug("Checking Snowflake service incidents...")
        fetch_snowflake_incidents()

def fetch_snowflake_incidents():
    """
    Fetches Snowflake incidents from the API.
    In test mode, simulated incidents are used.
    """
    if testMode:
        logger.debug("Simulating Snowflake incidents in test mode.")
        simulated_incident = {
            "id": "test-event-12345",
            "name": "Test Snowflake Outage",
            "status": "investigating",
            "started_at": "2024-09-10T12:00:00Z",
            "shortlink": "https://status.snowflake.com/incidents/test-event-12345",
            "incident_updates": [
                {"body": "<p>Initial analysis indicates an issue with data warehouse operations.</p>"}
            ]
        }
        process_incident(simulated_incident)
    else:
        url = "https://status.snowflake.com/api/v2/incidents.json"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            incidents_data = response.json().get('incidents', [])
            if incidents_data:
                latest_incident = incidents_data[0]
                process_incident(latest_incident)
            else:
                logger.info("No current incidents found.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Snowflake incidents: {e}")

def process_incident(incident):
    """
    Processes the incident and logs it if necessary.
    """
    platform = "Snowflake"
    event_name = f"{incident['name']} {incident['id']}"
    status = incident['status']
    impact_start_time = incident.get('started_at', 'N/A')
    link = incident.get('shortlink', 'N/A')
    event_id = incident['id']

    # Log the event with the Event Tracker
    event_data = {
        "platform": platform,
        "event_name": event_name,
        "status": status,
        "impact_start_time": impact_start_time,
        "description": format_incident_description(incident)
    }

    internal_id = event_tracker.log_event(event_data)
    
    # Construct the message
    message = (
        f"**Platform:** {platform}\n"
        f"**Event Name:** {event_name}\n"
        f"**Status:** {status}\n"
        f"**Impact Start Time:** {impact_start_time}\n"
        f"**Link:** {link}\n"
        f"**Description:** {event_data['description']}\n"
        f"**Internal ID:** {internal_id}\n"
    )

    # Log the event (or send to Slack, etc.)
    logger.info(f"Service health event data:\n{message}")

def format_incident_description(incident):
    """
    Aggregate descriptions from all incident updates and format the description.
    """
    incident_updates = incident.get('incident_updates', [])
    descriptions = [clean_html_content(update['body']) for update in incident_updates]
    description = "\n\n".join(descriptions).strip()

    # Extract and format the "Status Update:" sections
    updates = extract_and_format_updates(description)

    # Format the full description with updates
    return format_description(description, updates)

def clean_html_content(html_content):
    """Convert HTML to plain text and preserve formatting."""
    text_maker = html2text.HTML2Text()
    text_maker.ignore_links = True
    text_maker.bypass_tables = False
    text_maker.body_width = 0  # Preserve original line breaks
    plain_text = text_maker.handle(html_content)
    plain_text = re.sub(r'\n\s*\n', '\n\n', plain_text).strip()
    return plain_text

def extract_and_format_updates(description):
    """Extract 'Current status:' updates and format them in reverse order."""
    updates = re.findall(r'Current status:.*?(?=\n\n|\Z)', description, re.DOTALL)
    updates.reverse()  # Reverse the order to present the most recent first
    
    # Replace "Current status:" with "Status Update:"
    formatted_updates = "\n\n".join(update.replace("Current status:", "Status Update:") for update in updates).strip()
    
    if formatted_updates:
        return f"\n\n**Updates:**\n{formatted_updates}"
    else:
        return ""

def format_description(description, updates):
    """Format the description text and insert updates."""
    # Add new lines before specific keywords
    keywords = [
        "Customer experience:", "Incident start time:", 
        "Incident end time:", "Preliminary root cause:", "Final status:",
        "Next steps:"
    ]
    
    for keyword in keywords:
        description = re.sub(f'(?<!\n\n){keyword}', f'\n\n{keyword}', description)
    
    # Remove duplicates
    seen = set()
    lines = []
    for line in description.splitlines():
        if line.strip() not in seen and "Current status:" not in line:
            seen.add(line.strip())
            lines.append(line)
    formatted_description = "\n".join(lines)
    
    # Ensure consistent spacing
    formatted_description = re.sub(r'\*\*(\w)', r'** \1', formatted_description)
    formatted_description = re.sub(r'(\w)\*\*', r'\1 **', formatted_description)
    
    # Append updates
    if updates:
        formatted_description += updates
    
    return formatted_description

if __name__ == "__main__":
    SnowflakeServiceChecker.check_service()
