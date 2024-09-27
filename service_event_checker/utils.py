import os
from azure.data.tables import TableServiceClient, TableEntity
from flask import current_app
import requests

def get_table_service_client():
    """
    Returns an Azure Table Service client using the connection string from environment variables.
    """
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    return TableServiceClient.from_connection_string(connection_string)

def check_existing_ticket(event_id):
    """
    Checks if an existing Azure DevOps ticket is present for a given event ID.
    """
    table_service_client = get_table_service_client()
    table_client = table_service_client.get_table_client("EventTickets")
    try:
        entity = table_client.get_entity(partition_key='Tickets', row_key=event_id)
        current_app.logger.info(f"Found existing ticket for event: {event_id}")
        return entity['WorkItemId']
    except Exception as e:
        current_app.logger.info(f"No existing ticket found for event: {event_id}")
        return None

def store_ticket(event_id, work_item_id):
    """
    Stores a new ticket in the 'EventTickets' table for the given event ID.
    """
    table_service_client = get_table_service_client()
    table_client = table_service_client.get_table_client("EventTickets")
    entity = TableEntity()
    entity['PartitionKey'] = 'Tickets'
    entity['RowKey'] = event_id
    entity['WorkItemId'] = work_item_id
    table_client.upsert_entity(entity)
    current_app.logger.info(f"Stored ticket: {work_item_id} for event: {event_id}")

def move_to_resolved_events(event_id, event_data):
    """
    Moves an event to the 'ResolvedEvents' table and removes it from 'EventTickets'.
    """
    table_service_client = get_table_service_client()
    resolved_table_client = table_service_client.get_table_client("ResolvedEvents")
    active_table_client = table_service_client.get_table_client("EventTickets")

    entity = TableEntity()
    entity['PartitionKey'] = 'Resolved'
    entity['RowKey'] = event_id
    entity.update(event_data)

    resolved_table_client.upsert_entity(entity)
    active_table_client.delete_entity(partition_key='Tickets', row_key=event_id)
    current_app.logger.info(f"Moved event {event_id} to resolved events")

def list_tracked_events():
    """
    Lists all events currently tracked in the 'EventTickets' table.
    """
    table_service_client = get_table_service_client()
    table_client = table_service_client.get_table_client("EventTickets")
    entities = list(table_client.list_entities())
    current_app.logger.info(f"Listing {len(entities)} tracked events")
    return entities

def resolve_event(event_id):
    """
    Resolves an event by moving it from 'EventTickets' to 'ResolvedEvents'.
    """
    table_service_client = get_table_service_client()
    table_client = table_service_client.get_table_client("EventTickets")
    resolved_client = table_service_client.get_table_client("ResolvedEvents")

    entity = table_client.get_entity(partition_key='Tickets', row_key=event_id)
    resolved_client.upsert_entity(entity)
    table_client.delete_entity(partition_key='Tickets', row_key=event_id)
    current_app.logger.info(f"Resolved event: {event_id}")

def create_ado_work_item(platform, event_name, description):
    """
    Creates a new Azure DevOps work item for a given service event.
    """
    ado_org_url = os.getenv("ADO_ORG_URL")
    ado_project = os.getenv("ADO_PROJECT")
    ado_pat = os.getenv("ADO_PAT_BASE64")  # Use the Base64 encoded PAT
    url = f"{ado_org_url}/{ado_project}/_apis/wit/workitems/$Outage?api-version=6.0"
    headers = {
        'Content-Type': 'application/json-patch+json',
        'Authorization': f'Basic {ado_pat}',  # Use the Base64 encoded PAT
    }
    data = [
        {"op": "add", "path": "/fields/System.Title", "value": f"{platform} Outage - {event_name}"},
        {"op": "add", "path": "/fields/System.Description", "value": description},
    ]
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        work_item = response.json()
        current_app.logger.info(f"Created Azure DevOps work item: {work_item['id']}")
        return work_item
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error creating Azure DevOps ticket: {e}")
        raise
