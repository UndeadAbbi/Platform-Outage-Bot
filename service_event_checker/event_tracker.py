from azure.data.tables import TableServiceClient, TableClient
from azure.core.exceptions import ResourceExistsError
import os

class EventTracker:
    def __init__(self, test_mode=False):
        self.test_mode = test_mode
        if self.test_mode:
            # In-memory store for test mode
            self.event_store = {}
            self.next_internal_id = 1
        else:
            # Azure Table Storage setup
            self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            self.table_name = os.getenv("EVENT_TABLE_NAME", "TrackedEvents")
            self.service_client = TableServiceClient.from_connection_string(self.connection_string)
            self.table_client = self.service_client.get_table_client(self.table_name)
            self._ensure_table_exists()

    def _ensure_table_exists(self):
        """
        Ensures that the Azure Table for tracking events exists.
        """
        try:
            self.table_client.create_table()
        except ResourceExistsError:
            pass

    def get_next_internal_id(self):
        """
        Generates the next internal ID for events.
        In test mode, it uses an in-memory counter. In production, it queries the last entity from Azure Table Storage.
        """
        if self.test_mode:
            internal_id = f"{self.next_internal_id:04d}"
            self.next_internal_id += 1
            return internal_id
        else:
            # Query the last inserted event to get the latest ID
            entities = self.table_client.query_entities(select=["RowKey"], results_per_page=1)
            last_id = max([int(entity["RowKey"]) for entity in entities], default=0)
            return f"{last_id + 1:04d}"

    def log_event(self, event_data):
        """
        Logs a new event or retrieves the Internal ID for an existing event.
        In test mode, the event is stored in-memory. In production, it is stored in Azure Table Storage.
        """
        event_name = event_data["event_name"]
        platform = event_data["platform"]

        if self.test_mode:
            # In-memory mock for test mode
            for event_id, event in self.event_store.items():
                if event["event_name"] == event_name and event["platform"] == platform:
                    return event_id  # Event already exists, return its Internal ID

            # New event, assign an Internal ID
            internal_id = self.get_next_internal_id()
            self.event_store[internal_id] = event_data
            return internal_id
        else:
            # Check if event already exists in Azure Table Storage
            filter_query = f"PartitionKey eq '{platform}' and event_name eq '{event_name}'"
            existing_events = self.table_client.query_entities(filter=filter_query)

            for event in existing_events:
                return event["RowKey"]  # Event already exists, return its Internal ID

            # New event, insert into Azure Table Storage
            internal_id = self.get_next_internal_id()
            event_data["PartitionKey"] = platform
            event_data["RowKey"] = internal_id
            self.table_client.create_entity(entity=event_data)
            return internal_id

    def resolve_event(self, internal_id):
        """
        Marks an event as resolved based on its Internal ID.
        """
        if self.test_mode:
            if internal_id in self.event_store:
                self.event_store[internal_id]["status"] = "resolved"
        else:
            entity = self.table_client.get_entity(partition_key="TrackedEvents", row_key=internal_id)
            entity["status"] = "resolved"
            self.table_client.update_entity(entity)

    def get_event_by_id(self, internal_id):
        """
        Retrieves an event by its Internal ID.
        """
        if self.test_mode:
            return self.event_store.get(internal_id)
        else:
            return self.table_client.get_entity(partition_key="TrackedEvents", row_key=internal_id)

    def list_tracked_events(self):
        """
        Lists all currently tracked events.
        """
        if self.test_mode:
            return list(self.event_store.values())
        else:
            return list(self.table_client.list_entities())
