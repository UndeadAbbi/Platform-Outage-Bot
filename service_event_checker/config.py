import os
import json
from dotenv import load_dotenv

CONFIG_FILE = "config.json"  # File to store config state

# Load environment variables from .env file (for local development)
def init_env_variables():
    """
    Load environment variables from a .env file if available.
    Call this function at the start of your application.
    """
    load_dotenv()

# Get an environment variable with an optional default
def get_env_variable(key, default=None):
    """
    Retrieves an environment variable by key.
    Returns a default value if the environment variable is not set.
    """
    return os.getenv(key, default)

# Test Mode Management
def get_test_mode():
    """
    Retrieves the current test mode state from the config file.
    Returns False by default if the config file doesn't exist.
    """
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as file:
            config = json.load(file)
            return config.get('testMode', False)
    return False

def set_test_mode(state):
    """
    Updates the test mode state in the config file.
    """
    config = {"testMode": state}
    with open(CONFIG_FILE, 'w') as file:
        json.dump(config, file)

def toggle_test_mode(state):
    """
    Toggles the test mode state and updates the config file.
    Returns the updated state.
    """
    set_test_mode(state)
    return state

# Custom Helpers for Specific Environment Variables
def get_azure_storage_connection_string():
    """
    Retrieves the Azure Storage connection string from environment variables.
    """
    return get_env_variable("AZURE_STORAGE_CONNECTION_STRING", "DefaultConnectionString")

def get_slack_bot_token():
    """
    Retrieves the Slack bot token from environment variables.
    """
    return get_env_variable("SLACK_BOT_TOKEN", "DefaultSlackToken")

def get_ado_pat_token():
    """
    Retrieves the Azure DevOps PAT token from environment variables.
    """
    return get_env_variable("ADO_PAT_BASE64", "DefaultPATToken")

