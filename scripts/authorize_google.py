"""Run locally after downloading the single desktop OAuth client JSON."""
import json
import os
import sys
from integration_config import ROOT, load_env, private_write


def main():
    env = load_env()
    path = ROOT / env['GOOGLE_CREDENTIALS_FILE']
    if not path.exists() or path.is_symlink():
        raise SystemExit('Download desktop OAuth client credentials.json into the project first.')
    os.chmod(path, 0o600)
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.oauth2.credentials import Credentials
    except ImportError:
        raise SystemExit('Install scripts/requirements-integrations.txt in a project virtual environment first.')
    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(path), env['GOOGLE_OAUTH_SCOPES'].split())
        # The URL carries no client secret or authorization token. Library opens
        # the official Google consent page; the callback binds loopback only.
        # Google can otherwise reuse a prior consent grant without returning a
        # refresh token.  A long-running trigger worker needs a refreshable
        # offline credential, not a short-lived access token.
        creds = flow.run_local_server(host='127.0.0.1', port=8765, open_browser=True,
                                      authorization_prompt_message='Complete consent in your local browser.',
                                      success_message='Authorization saved locally. You can close this tab.',
                                      access_type='offline', prompt='consent')
        token = creds.to_json()
        # Validate the shape before replacing a previously working token. This
        # check uses no network and never prints credential fields.
        validated = Credentials.from_authorized_user_info(json.loads(token))
        if not validated.refresh_token:
            raise ValueError('refresh token missing')
        private_write(ROOT / env['GOOGLE_TOKEN_FILE'], token)
    except Exception:
        raise SystemExit('Google authorization failed. No error details logged; retry in your local terminal.')
    print('Google token saved securely. Run scripts/validate_integrations.py next.')


if __name__ == '__main__':
    main()
