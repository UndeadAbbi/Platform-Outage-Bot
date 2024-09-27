import logging
import requests
import html2text
import os
import re
from dotenv import load_dotenv
from service_event_checker.event_tracker import EventTracker  # Import the Event Tracker
from service_event_checker.config import get_test_mode, init_env_variables

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

class O365ServiceChecker:
    @staticmethod
    def check_service():
        logger.debug("Checking service health issues...")
        fetch_current_service_health_issues()

def get_access_token():
    """
    Retrieves the access token from Azure AD using client credentials.
    In test mode, a mock token is returned.
    """
    if testMode:
        logger.debug("Using mock access token in test mode.")
        return "mock_access_token"
    
    tenant_id = os.getenv("TENANT_ID")
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    body = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default"
    }
    response = requests.post(token_url, headers=headers, data=body)
    response.raise_for_status()
    return response.json().get("access_token")

def fetch_current_service_health_issues():
    """
    Fetches the current Office 365 service health issues.
    In test mode, simulated issues are used.
    """
    if testMode:
        # Simulated test data
        issues = [
            {
                'id': 'test-issue-1',
                'title': 'Test Issue: Service Degradation',
                'status': 'investigating',
                'service': 'Exchange Online',
                'startDateTime': '2024-09-10T12:00:00Z',
                'posts': [
                    {
                        'description': {
                            'content': '<p>Initial analysis indicates an issue with mail flow...</p>'
                        }
                    }
                ]
            }
        ]
        logger.debug(f"Simulated issues: {issues}")
        for issue in issues:
            process_issue(issue)
    else:
        token = get_access_token()
        url = "https://graph.microsoft.com/v1.0/admin/serviceAnnouncement/issues"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            issues = response.json().get('value', [])
            logger.debug(f"Fetched {len(issues)} issues from O365 API.")
            for issue in issues:
                process_issue(issue)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Office 365 service health issues: {e}")

def clean_html_content(html_content):
    """Convert HTML to plain text and preserve formatting."""
    text_maker = html2text.HTML2Text()
    text_maker.ignore_links = True
    text_maker.bypass_tables = False
    text_maker.body_width = 0  # Preserve original line breaks
    plain_text = text_maker.handle(html_content)
    plain_text = re.sub(r'\n\s*\n', '\n\n', plain_text).strip()
    return plain_text

def format_description(description):
    """Format the description text by adding new lines before specific keywords and removing duplicates."""
    keywords = [
        "Current status:", "Scope of impact:", "Root cause:", "Next update by:",
        "Final status:", "Start time:", "End time:", "Next steps:", "User impact:"
    ]
    
    for keyword in keywords:
        pattern = rf'{keyword}.*?\.'
        matches = re.findall(pattern, description)
        if len(matches) > 1:
            for match in matches[1:]:
                description = description.replace(match, '')
    
    for keyword in keywords:
        description = re.sub(f'(?<!\n\n){keyword}', f'\n\n{keyword}', description)
    
    sentences = description.split('\n\n')
    seen = set()
    unique_sentences = []
    for sentence in sentences:
        if sentence not in seen:
            seen.add(sentence)
            unique_sentences.append(sentence)
    formatted_description = '\n\n'.join(unique_sentences)
    
    return formatted_description

def process_issue(issue):
    """
    Processes the issue and logs it if necessary.
    """
    platform = "O365"
    event_name = f"{issue['title']} {issue['id']}"
    status = issue['status']
    impacted_service = issue['service']
    impact_start_time = issue.get('startDateTime', 'N/A')

    posts = issue.get('posts', [])
    descriptions = [clean_html_content(post['description'].get('content', '')) for post in posts]
    description = "\n\n".join(descriptions).strip()
    
    description = re.sub(r'^Title:\s*', '', description, flags=re.MULTILINE)
    description = format_description(description)

    # Log the event and get its Internal ID
    event_data = {
        "platform": platform,
        "event_name": event_name,
        "status": status,
        "impact_start_time": impact_start_time,
        "description": description
    }

    internal_id = event_tracker.log_event(event_data)

    message = (
        f"**Platform:** {platform}\n"
        f"**Event Name:** {event_name}\n"
        f"**Status:** {status}\n"
        f"**Impacted Service:** {impacted_service}\n"
        f"**Impact Start Time:** {impact_start_time}\n"
        f"**Description:**\n{description}\n"
        f"**Internal ID:** {internal_id}\n"
    )

    logger.info(f"Service health event data:\n{message}")

if __name__ == "__main__":
    O365ServiceChecker.check_service()
