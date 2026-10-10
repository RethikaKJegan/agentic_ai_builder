"""Server-owned polling adapters for published provider trigger bindings."""
from __future__ import annotations

import hashlib
import json


class ProviderTriggerSource:
    """Resolve polling through the same Registry grants as runtime actions."""
    TOOL_BY_PROVIDER = {
        "google_sheets": "google_sheets_read_rows",
        "google_drive": "google_drive_list_files",
        "google_calendar": "google_calendar_list_events",
        "google_docs": "google_docs_read",
        "generic_rest": "generic_rest_request",
        "open_meteo": "open_meteo_forecast",
        "open_library": "open_library_search",
    }

    def __init__(self, service, connectors, default_resources=None):
        self.service, self.connectors = service, connectors
        self.default_resources = dict(default_resources or {})

    def _authority(self, binding):
        with self.service.store.transaction() as db:
            row = db.execute("SELECT r.document FROM lifecycle_releases r JOIN lifecycle_triggers t ON t.release_id=r.release_id WHERE t.binding_id=? AND t.workspace=?",
                             (binding['binding_id'], binding['workspace_id'])).fetchone()
            if not row:
                raise ValueError("release missing")
            release = json.loads(row[0])
            identity = db.execute("SELECT authority FROM lifecycle_identities WHERE identity_id=?", (release["automation_identity_id"],)).fetchone()
            if not identity:
                raise ValueError("identity missing")
            workflow = self.service.store.get(db, binding["workspace_id"], release["revision"]["workflow_id"], release["revision"]["workflow_version"])
        return workflow, json.loads(identity[0])

    def poll(self, binding, previous_cursor):
        provider = binding["provider_id"]
        tool_id = self.TOOL_BY_PROVIDER.get(provider)
        if not tool_id:
            raise ValueError("poll provider needs a configured adapter")
        connector = self.connectors.get(tool_id)
        if connector is None:
            raise ValueError("poll connector unavailable")
        workflow, auth = self._authority(binding)
        grants = self.service.registry_adapter.execution_assignments(workflow, auth)
        grant = next((item for item in grants if item["tool_id"] == tool_id), None)
        if grant is None:
            raise ValueError("poll tool is not authorized")
        resource_id = binding["resource_id"]
        if resource_id == "configured_default":
            resource_id = self.default_resources.get(provider)
        if not isinstance(resource_id, str) or not resource_id:
            raise ValueError("poll resource is not configured")
        inputs = dict(binding.get("poll_input") or {})
        if provider == "google_sheets":
            from runtime.connectors import google_spreadsheet_id
            resource_id = google_spreadsheet_id(resource_id)
            inputs = {"spreadsheet_id": resource_id, "range": inputs.get("range", "A:Z")}
        if hasattr(connector, "poll_changes"):
            options = {}
            if provider == 'google_sheets' and binding.get('event_type') == 'row.created':
                options = dict(event_type='row.created', identity_field=binding['poll_input'].get('identity_field'),
                               required_fields=binding['poll_input'].get('required_fields', []), baseline_policy=binding.get('baseline_policy', 'current_only'))
            result = connector.poll_changes(grant, inputs, previous_cursor, **options)
            changes = [{**event, "spreadsheet_id": resource_id, "range": inputs["range"]} for event in result["changes"]]
            return changes, result["cursor"]
        output = connector.invoke(grant, inputs, "poll:" + (previous_cursor or "initial"))
        cursor = hashlib.sha256(json.dumps(output, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        changes = [] if cursor == previous_cursor else [{"event_id": f"snapshot:{provider}:{cursor}", "provider": provider, "data": output}]
        return changes, cursor
