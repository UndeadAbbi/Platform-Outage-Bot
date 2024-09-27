import logging
import requests
import html2text
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import os
from service_event_checker.event_tracker import EventTracker  # Import the Event Tracker
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

# Initialize the Event Tracker
event_tracker = EventTracker(test_mode=testMode)

class ReToolServiceChecker:
    @staticmethod
    def check_service():
        logger.debug("Checking Retool service health...")
        fetch_latest_retool_event()

def fetch_latest_retool_event():
    """
    Fetches the latest Retool event from their RSS feed.
    In test mode, simulated events are used.
    """
    if testMode:
        logger.debug("Simulating Retool service event in test mode.")
        simulated_event = {
            'event_id': 'test-retool-event-1',
            'title': 'Test Retool Outage',
            'description': '<strong>Investigating</strong> - We are currently investigating an issue with Retool.',
            'pub_date': '2024-09-10T12:00:00Z',
            'link': 'https://status.retool.com/incidents/test-retool-event-1'
        }
        process_retool_event(simulated_event)
    else:
        url = "https://status.retool.com/history.rss"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            parse_and_log_retool_event(response.content)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Retool service event: {e}")

def clean_html_content(html_content):
    """Convert HTML to plain text and preserve formatting."""
    text_maker = html2text.HTML2Text()
    text_maker.ignore_links = True
    text_maker.bypass_tables = False
    text_maker.body_width = 0  # Preserve original line breaks
    plain_text = text_maker.handle(html_content)
    return plain_text.strip()

def parse_and_log_retool_event(xml_content):
    """
    Parses the RSS feed XML content and processes the latest event.
    """
    root = ET.fromstring(xml_content)
    latest_item = root.find('channel/item')
    
    if latest_item is not None:
        event_title = latest_item.find('title').text
        event_description = latest_item.find('description').text
        event_pub_date = latest_item.find('pubDate').text
        event_link = latest_item.find('link').text
        
        # Extract the event ID from the link (assuming the ID is part of the URL)
        event_id = event_link.split('/')[-1]
        
        # Extract status from the description
        status_start = event_description.find('<strong>') + len('<strong>')
        status_end = event_description.find('</strong>')
        event_status = event_description[status_start:status_end] if status_start != -1 and status_end != -1 else "Unknown"
        
        # Clean and format the description
        description = clean_html_content(event_description)
        
        # Process the event
        process_retool_event({
            'event_id': event_id,
            'title': event_title,
            'description': description,
            'status': event_status,
            'pub_date': event_pub_date,
            'link': event_link
        })
    else:
        logger.info("No events found in Retool feed.")

def process_retool_event(event):
    """
    Processes the event and logs it if necessary.
    """
    event_id = event['event_id']
    event_title = event['title']
    event_status = event.get('status', 'Unknown')
    event_description = event['description']
    event_pub_date = event['pub_date']
    event_link = event['link']

    # Log the event with the Event Tracker
    event_data = {
        "platform": "ReTool",
        "event_name": event_title,
        "status": event_status,
        "impact_start_time": event_pub_date,
        "description": event_description
    }
    internal_id = event_tracker.log_event(event_data)
    
    # Construct the message
    message = (
        f"**Platform:** ReTool\n"
        f"**Event Name:** {event_title}\n"
        f"**Status:** {event_status}\n"
        f"**Link:** {event_link}\n"
        f"**Impact Start Time:** {event_pub_date}\n"
        f"**Description:**\n{event_description}\n"
        f"**Internal ID:** {internal_id}\n"
    )
    
    # Log the event (or send to Slack, etc.)
    logger.info(f"Service health event data:\n{message}")

if __name__ == "__main__":
    ReToolServiceChecker.check_service()
