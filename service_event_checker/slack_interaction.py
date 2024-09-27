import os
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from service_event_checker.config import get_ado_pat_token, get_slack_bot_token

# Initialize Slack client using environment variable for the token
slack_client = WebClient(token=get_slack_bot_token())

# In-memory storage to track ticket creation (In production, use persistent storage)
created_tickets = set()

# Azure DevOps information from environment variables
ADO_ORG_URL = os.getenv('ADO_ORG_URL')
ADO_PROJECT = os.getenv('ADO_PROJECT')
ADO_PAT_BASE64 = get_ado_pat_token()

def post_incident_message(channel, event_data):
    """
    Posts a formatted service incident message to the specified Slack channel.
    Includes an interactive button for creating tickets.
    """
    try:
        slack_client.chat_postMessage(
            channel=channel,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*Platform:* {event_data['platform']}\n"
                            f"*Event Name:* {event_data['event_name']}\n"
                            f"*Status:* {event_data['status']}\n"
                            f"*Impact Start Time:* {event_data['impact_start_time']}\n"
                            f"*Description:*\n{event_data['description']}\n"
                            f"*Internal ID:* {event_data['internal_id']}"
                        )
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Create Ticket"},
                            "value": event_data['internal_id'],
                            "action_id": "create_ticket"
                        }
                    ]
                }
            ],
            text=f"Service Health Incident: {event_data['event_name']}"
        )
    except SlackApiError as e:
        print(f"Error posting to Slack: {e.response['error']}")

def handle_interactive_action(payload):
    """
    Handles the interaction from the Slack button click (e.g., Create Ticket button).
    """
    action = payload['actions'][0]
    internal_id = action['value']
    user_id = payload['user']['id']
    
    if action['action_id'] == "create_ticket":
        # Check if a ticket has already been created for this incident
        if internal_id in created_tickets:
            # Ticket already created, ask for confirmation
            send_confirmation_message(payload['channel']['id'], internal_id, user_id)
        else:
            # Create a new ticket
            create_azure_devops_ticket(internal_id, payload['channel']['id'], user_id)

def send_confirmation_message(channel, internal_id, user_id):
    """
    Sends a confirmation message to the user when they attempt to create a duplicate ticket.
    """
    try:
        slack_client.chat_postMessage(
            channel=channel,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"<@{user_id}>, a ticket has already been created for this event (ID: {internal_id}). Do you want to create another ticket?"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Yes, create another"},
                            "value": internal_id,
                            "action_id": "confirm_create_ticket"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "No, cancel"},
                            "value": internal_id,
                            "action_id": "cancel_create_ticket"
                        }
                    ]
                }
            ],
            text="Duplicate Ticket Confirmation"
        )
    except SlackApiError as e:
        print(f"Error sending confirmation to Slack: {e.response['error']}")

def create_azure_devops_ticket(internal_id, channel, user_id):
    """
    Creates an 'Outage' work item in Azure DevOps for the given service event.
    """
    url = f"{ADO_ORG_URL}/{ADO_PROJECT}/_apis/wit/workitems/$Outage?api-version=6.0"
    headers = {
        'Content-Type': 'application/json-patch+json',
        'Authorization': f'Basic {ADO_PAT_BASE64}'  # PAT Base64-encoded
    }

    # Example event data structure
    event_data = {
        "platform": "Slack",
        "event_name": "Test Slack Incident",
        "status": "active",
        "impact_start_time": "2024-09-10T12:00:00Z",
        "description": "We are currently investigating an issue with Slack.",
        "internal_id": internal_id
    }

    # Construct the full message (same as what is posted in Slack)
    full_message = (
        f"**Platform:** {event_data['platform']}\n"
        f"**Event Name:** {event_data['event_name']}\n"
        f"**Status:** {event_data['status']}\n"
        f"**Impact Start Time:** {event_data['impact_start_time']}\n"
        f"**Description:**\n{event_data['description']}\n"
        f"**Internal ID:** {event_data['internal_id']}"
    )

    # Work item data for Azure DevOps
    work_item_data = [
        {
            "op": "add",
            "path": "/fields/System.Title",
            "value": f"{event_data['platform']} Outage - {event_data['event_name']}"
        },
        {
            "op": "add",
            "path": "/fields/System.Description",
            "value": full_message  # The entire message goes into the description field
        }
    ]

    try:
        response = requests.post(url, json=work_item_data, headers=headers)
        response.raise_for_status()
        created_tickets.add(internal_id)

        # Notify in Slack that the ticket was created
        slack_client.chat_postMessage(
            channel=channel,
            text=f"Outage ticket successfully created by <@{user_id}> for event (ID: {internal_id})."
        )
    except requests.exceptions.RequestException as e:
        print(f"Error creating Azure DevOps ticket: {e}")
        slack_client.chat_postMessage(
            channel=channel,
            text=f"Error creating ticket for event (ID: {internal_id})."
        )

# Example event data for testing
event_data_example = {
    "platform": "Slack",
    "event_name": "Test Slack Incident",
    "status": "active",
    "impact_start_time": "2024-09-10T12:00:00Z",
    "description": "We are currently investigating an issue with Slack.",
    "internal_id": "0013"
}

# Post to a specific Slack channel (replace with actual channel ID)
#post_incident_message("#general", event_data_example)
