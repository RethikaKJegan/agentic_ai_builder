"""Configure one personal DM source and prepare an unapproved mapped draft."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.integration_config import private_write
from workflow_api.slack_gmail import SETTINGS, REGISTRY, environment, validate_settings, registry_configuration, prepare_draft
from workflow_api.main import create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--team-id')
    parser.add_argument('--conversation-id')
    parser.add_argument('--sender-id', default=None)
    parser.add_argument('--recipient')
    args = parser.parse_args()
    env = environment()
    previous = json.loads(SETTINGS.read_text()) if SETTINGS.exists() else {}
    def choose(key, supplied, prompt, default=''):
        if supplied is not None:
            return supplied.strip()
        value = previous.get(key, default)
        return input(prompt + (f' [{value}]' if value else '') + ': ').strip() or value
    settings = dict(team_id=choose('team_id', args.team_id, 'Slack workspace/team ID (T...)'),
                    conversation_id=choose('conversation_id', args.conversation_id, 'Personal DM conversation ID (D...)'),
                    sender_id=choose('sender_id', args.sender_id, 'Sender member ID (U...; empty allows any sender in this DM)'),
                    recipient=choose('recipient', args.recipient, 'Notification recipient', env.get('GMAIL_SMTP_USER', '')))
    validate_settings(settings)
    configuration = registry_configuration(env)
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    private_write(REGISTRY, json.dumps(configuration, indent=2) + '\n')
    app = create_app(dev_auth=True, roles=['admin', 'approver'], runtime_enabled=True, registry_config=REGISTRY, start_workers=False)
    created = prepare_draft(app.state.workflow_service, settings)
    private_write(SETTINGS, json.dumps(settings, indent=2) + '\n')
    print('Settings saved. ' + ('Created Slack DM → Gmail draft.' if created else 'Existing Slack DM → Gmail draft preserved.'))
    print('Open the workflow in the UI, then Save/Validate, Approve and Publish. Each email requires run approval.')
    if not env.get('SLACK_APP_TOKEN'):
        print('Next: python3 scripts/set_integration_secret.py SLACK_APP_TOKEN')


if __name__ == '__main__':
    try:
        main()
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    except OSError:
        raise SystemExit('Setup files could not be read or saved. Check project file permissions.') from None
