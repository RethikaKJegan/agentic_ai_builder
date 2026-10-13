"""Independent OAuth consent helper; never overwrites original credentials/token."""
import argparse
import os
from pathlib import Path
from .catalog import CATALOG, GOOGLE


def required_scopes(providers):
    scopes = {GOOGLE + scope for tool in CATALOG.values() if tool['provider_id'] in providers
              for scope in tool['authentication']['scopes'] if scope != 'web.search'}
    for full, read in [('spreadsheets', 'spreadsheets.readonly'), ('calendar.events', 'calendar.events.readonly')]:
        if GOOGLE + full in scopes: scopes.discard(GOOGLE + read)
    return sorted(scopes)


def save_credentials(credentials, path, requested):
    from scripts.integration_config import private_write
    grants = set(credentials.granted_scopes or [])
    for full, read in [('spreadsheets', 'spreadsheets.readonly'), ('calendar.events', 'calendar.events.readonly')]:
        if GOOGLE + full in grants: grants.add(GOOGLE + read)
    if not credentials.refresh_token or not set(requested) <= grants:
        raise ValueError('Google did not return verified offline grants; the extension token was preserved.')
    if Path(path).is_symlink(): raise ValueError('The extension token cannot be a symlink.')
    private_write(path, credentials.to_json())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client', required=True, type=Path, help='Read-only path to an existing Google OAuth client JSON.')
    parser.add_argument('--providers', nargs='+', choices=['google_sheets', 'google_calendar', 'gmail'], required=True)
    parser.add_argument('--state-dir', type=Path)
    parser.add_argument('--callback-port', type=int, default=8766)
    parser.add_argument('--no-browser', action='store_true', help='Print the consent URL for a browser/tunneled callback.')
    args = parser.parse_args()
    from .app import state_directory
    from google_auth_oauthlib.flow import InstalledAppFlow
    requested = required_scopes(args.providers)
    try:
        state = state_directory(args.state_dir)
        flow = InstalledAppFlow.from_client_secrets_file(str(args.client), scopes=requested)
        credentials = flow.run_local_server(host='127.0.0.1', port=args.callback_port, open_browser=not args.no_browser,
            access_type='offline', prompt='consent', authorization_prompt_message='Authorize the separate connector extension in your browser: {url}',
            success_message='Callback received. Check the terminal for the extension authorization result.')
        save_credentials(credentials, state / 'google-token.json', requested)
    except Exception:
        parser.exit(1, 'Extension Google consent was not saved. Check the client, callback and requested permissions; original credentials were not changed.\n')
    print('Verified extension consent saved privately in the extension state directory.')

if __name__ == '__main__': main()
