import os
import requests
from flask import Blueprint, request, jsonify, current_app
from service_event_checker.utils import check_existing_ticket, store_ticket, move_to_resolved_events, resolve_event, create_ado_work_item, list_tracked_events
from ServiceCheckers.SlackServiceChecker import SlackServiceChecker
from ServiceCheckers.AzureServiceChecker import AzureServiceChecker
from ServiceCheckers.GithubServiceChecker import GithubServiceChecker
from ServiceCheckers.O365ServiceChecker import O365ServiceChecker
from ServiceCheckers.ReToolServiceChecker import ReToolServiceChecker
from ServiceCheckers.SalesforceServiceChecker import SalesforceServiceChecker
from ServiceCheckers.SnowflakeServiceChecker import SnowflakeServiceChecker
from ServiceCheckers.ADOServiceChecker import ADOServiceChecker
from .event_tracker import EventTracker
from .config import set_test_mode

bp = Blueprint('main', __name__)

@bp.route("/", methods=["GET"])
def index():
    current_app.logger.info("Index route accessed")
    return jsonify({"message": "Service Event Checker is running!"}), 200

def initialize_event_tracker():
    test_mode = current_app.config.get('testMode', False)
    return EventTracker(test_mode=test_mode)

### /BotStatus ###
@bp.route("/slack/bot-status", methods=["POST"])
def bot_status():
    try:
        # Health check logic for your app, checking essential services and databases.
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "reason": str(e)}), 500

### /TestModeOn ###
@bp.route("/slack/test-mode-on", methods=["POST"])
def test_mode_on():
    set_test_mode(True)
    current_app.logger.info("Test mode turned ON")
    return jsonify({"response_type": "in_channel", "text": "Test mode is now ON"}), 200

### /TestModeOff ###
@bp.route("/slack/test-mode-off", methods=["POST"])
def test_mode_off():
    set_test_mode(False)
    current_app.logger.info("Test mode turned OFF")
    return jsonify({"response_type": "in_channel", "text": "Test mode is now OFF"}), 200

### /ManualCheck {Platform} ###
@bp.route("/slack/manual-check", methods=["POST"])
def manual_check():
    platform = request.form.get('text').strip().lower()

    event_tracker = initialize_event_tracker()

    checkers = {
        'azure': AzureServiceChecker,
        'ado': ADOServiceChecker,
        'slack': SlackServiceChecker,
        'salesforce': SalesforceServiceChecker,
        'snowflake': SnowflakeServiceChecker,
        'github': GithubServiceChecker,
        'o365': O365ServiceChecker,
        'retool': ReToolServiceChecker
    }

    if platform not in checkers:
        return jsonify({"response_type": "ephemeral", "text": f"Invalid platform: {platform}"}), 400

    # Run the service checker for the selected platform
    checkers[platform].check_service(event_tracker)  # Pass event_tracker instance
    return jsonify({"response_type": "in_channel", "text": f"Manual check for {platform.capitalize()} has been triggered"}), 200

### /CreateTicket {Internal ID} ###
@bp.route("/slack/create-ticket", methods=["POST"])
def create_ticket():
    internal_id = request.form.get('text').strip()
    work_item = create_ado_work_item(internal_id)
    return jsonify({"response_type": "in_channel", "text": f"Ticket created for event ID {internal_id}: {work_item['id']}"}), 200

### /ForceResolve {Internal ID} ###
@bp.route("/slack/force-resolve", methods=["POST"])
def force_resolve():
    internal_id = request.form.get('text').strip()
    resolve_event(internal_id)
    return jsonify({"response_type": "in_channel", "text": f"Event ID {internal_id} has been forcefully resolved."}), 200

### /ListEvents ###
@bp.route("/slack/list-events", methods=["POST"])
def list_events():
    events = list_tracked_events()
    event_list = '\n'.join([f"- {event['RowKey']}: {event['event_name']}" for event in events])
    return jsonify({"response_type": "in_channel", "text": f"Currently tracked events:\n{event_list}"}), 200
