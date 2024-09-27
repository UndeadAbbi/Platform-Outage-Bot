from service_event_checker.config import get_test_mode, init_env_variables
import logging
from service_event_checker.event_tracker import EventTracker
import requests
import html2text
import re
from azure.identity import DefaultAzureCredential
from azure.mgmt.subscription import SubscriptionClient
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

class AzureServiceChecker:
    @staticmethod
    def check_service():
        subscriptions, disabled_subscriptions = get_azure_subscriptions()

        for subscription_id in subscriptions:
            fetch_service_health_events(subscription_id)

        if disabled_subscriptions:
            logger.warning(f"Skipped disabled subscriptions: {disabled_subscriptions}")

def clean_excessive_blank_lines(text):
    """Replace multiple consecutive blank lines with a maximum of two."""
    return re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

def get_azure_subscriptions():
    """
    Fetch Azure subscriptions using DefaultAzureCredential. 
    In test mode, simulate this data.
    """
    if testMode:
        # Simulated test subscription IDs
        subscriptions = ["test-subscription-1"]
        disabled_subscriptions = []
        return subscriptions, disabled_subscriptions
    else:
        credential = DefaultAzureCredential()
        subscription_client = SubscriptionClient(credential)
        subscriptions = []
        disabled_subscriptions = []

        for sub in subscription_client.subscriptions.list():
            if sub.state == "Enabled":
                subscriptions.append(sub.subscription_id)
            else:
                disabled_subscriptions.append(sub.subscription_id)

        return subscriptions, disabled_subscriptions

def fetch_service_health_events(subscription_id):
    """
    Fetch Azure service health events for a given subscription.
    In test mode, simulate the service health events.
    """
    if testMode:
        # Simulated service health event data
        events = [
            {
                'id': 'test-event-1',
                'name': 'Test Outage Event',
                'properties': {
                    'status': 'Active',
                    'title': 'Simulated Outage for Testing',
                    'impact': [
                        {
                            'impactedService': 'Compute',
                            'impactedRegions': [{'impactedRegion': 'US'}]
                        }
                    ],
                    'impactStartTime': '2024-09-10T12:00:00Z',
                    'description': 'Simulated description of a major outage affecting Compute services in the US.'
                }
            }
        ]
        for event in events:
            process_event(event)
    else:
        # Fetch real data in production
        credential = DefaultAzureCredential()
        token = credential.get_token("https://management.azure.com/.default").token
        url = f"https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.ResourceHealth/events?api-version=2024-02-01"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            events = response.json().get("value", [])
            for event in events:
                process_event(event)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching service health events for subscription {subscription_id}: {e}")

def process_event(event):
    event_id = event['id']
    event_name = event['name']
    status = event['properties']['status']
    impacted_service = event['properties']['impact'][0].get('impactedService', 'N/A')
    impact_start_time = event['properties'].get('impactStartTime', 'N/A')
    impacted_regions = [region['impactedRegion'] for region in event['properties']['impact'][0].get('impactedRegions', [])]
    description = clean_excessive_blank_lines(html2text.html2text(event['properties']['description']))

    # Skip regions that are not relevant in test mode
    if testMode or any(region == 'US' for region in impacted_regions):
        output_event(event, event_name, status, impacted_service, impact_start_time, description)

def output_event(event, event_name, status, impacted_service, impact_start_time, description):
    platform = "Azure"
    event_data = {
        "platform": platform,
        "event_name": event_name,
        "status": status,
        "impact_start_time": impact_start_time,
        "description": description
    }

    # Log the event and get its Internal ID
    internal_id = event_tracker.log_event(event_data)

    # Construct the message
    message = (
        f"**Platform:** {platform}\n"
        f"**Event Name:** {event['properties']['title']} {event_name}\n"
        f"**Status:** {status}\n"
        f"**Impacted Service:** {impacted_service}\n"
        f"**Impact Start Time:** {impact_start_time}\n"
        f"**Description:**\n{description}\n"
        f"**Internal ID:** {internal_id}\n"
    )

    # Clean up any excessive blank lines
    message = clean_excessive_blank_lines(message)

    # Log the event (or send to Slack, etc.)
    logger.warning(f"Service health event data:\n{message}")

if __name__ == "__main__":
    checker = AzureServiceChecker()
    checker.check_service()
