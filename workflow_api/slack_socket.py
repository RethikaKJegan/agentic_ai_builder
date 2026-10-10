"""Socket Mode ingress; payloads confer no workspace or execution authority."""
import json
import logging

from .lifecycle import LifecycleFailure

LOG = logging.getLogger(__name__)


class SlackSocketReceiver:
    def __init__(self, service, authenticate, team_id, conversation_id, sender_id='', client=None):
        self.service, self.authenticate = service, authenticate
        self.team_id, self.conversation_id, self.sender_id = team_id, conversation_id, sender_id
        self.client = client

    def route(self, payload):
        if not isinstance(payload, dict) or payload.get('type') != 'event_callback':
            return 0
        event = payload.get('event', {})
        if (payload.get('team_id') != self.team_id or not isinstance(event, dict) or
                event.get('type') != 'message' or event.get('channel_type') != 'im' or
                event.get('channel') != self.conversation_id or event.get('subtype') or
                event.get('bot_id') or not event.get('user') or
                (self.sender_id and event.get('user') != self.sender_id) or
                not isinstance(event.get('text'), str) or not isinstance(payload.get('event_id'), str)):
            return 0
        normalized = dict(event_id=payload['event_id'], team_id=self.team_id,
                          channel_id=event['channel'], sender_id=event['user'], actor_id=event['user'],
                          event_type='message.im', text=event['text'], body=event['text'],
                          timestamp=event.get('ts', ''))
        lifecycle = self.service.lifecycle
        with lifecycle.store.transaction() as db:
            rows = db.execute("SELECT document FROM lifecycle_triggers WHERE workspace='local-workspace' AND state='ready'").fetchall()
        routed = 0
        for row in rows:
            binding = json.loads(row[0])
            if (binding['provider_id'] != 'slack_events' or binding['delivery'] != 'push' or
                    binding['credential_reference'] != 'cred_slack_socket' or
                    binding['event_type'] != 'message.im' or binding['resource_id'] != self.conversation_id):
                continue
            auth = self.authenticate(binding['workspace_id'], 'local-builder')
            if auth is None:
                raise LifecycleFailure('SOURCE_AUTHORITY_UNAVAILABLE', 'Socket ingress identity is unavailable.', 403)
            try:
                result = lifecycle.ingest(binding['binding_id'], normalized, auth)
                routed += int(result.get('accepted', False))
            except LifecycleFailure as exc:
                # Permanent bad mappings are acknowledged; retries cannot fix them.
                if exc.code not in {'EVENT_SCHEMA_INVALID', 'EVENT_MAPPING_FAILED', 'SELF_ORIGINATED_EVENT', 'TRIGGER_NOT_ACTIVE'}:
                    raise
                LOG.warning('Slack event rejected: %s', exc.code)
        if not rows:
            LOG.info('Slack event received; no active workflow trigger.')
        return routed

    def process(self, client, request):
        try:
            if request.type == 'events_api':
                self.route(request.payload)
            # Relevant deliveries are acknowledged only after durable receipt commit.
            client.send_socket_mode_response({'envelope_id': request.envelope_id})
        except Exception:
            LOG.warning('Slack receipt was not committed; acknowledgment withheld for retry.')

    def start(self, app_token=None):
        if self.client is None:
            from slack_sdk.socket_mode import SocketModeClient
            # SDK debug logs can include raw envelopes. Keep SDK logging private.
            sdk_logger = logging.Logger('builder.slack_sdk', level=logging.CRITICAL)
            sdk_logger.addHandler(logging.NullHandler())
            self.client = SocketModeClient(app_token=app_token, logger=sdk_logger)
        self.client.socket_mode_request_listeners.append(self.process)
        try:
            self.client.connect()
        except Exception:
            self.stop()
            raise RuntimeError('Slack Socket Mode connection failed. Check SLACK_APP_TOKEN and connections:write.') from None
        LOG.info('Slack Socket Mode connected; waiting for configured DM events.')

    def stop(self):
        if self.client is not None:
            self.client.close()
