"""Authorize configured Google permissions in your own browser."""
import json
import argparse
import getpass
import hmac
import os
from functools import partial
from urllib.parse import urlparse, parse_qs
from integration_config import ROOT, load_env, private_write


class AuthorizationError(ValueError):
    """A fixed, credential-free message safe to display."""


def checked_scopes(requested, granted):
    granted = set(granted.split() if isinstance(granted, str) else granted or [])
    covered = set(granted)
    if 'https://www.googleapis.com/auth/spreadsheets' in granted:
        covered.add('https://www.googleapis.com/auth/spreadsheets.readonly')
    if set(requested) - covered:
        raise AuthorizationError('Required Google permissions were not granted. Retry and approve every requested permission, including Sheets editing.')
    return granted


def recover_scope_change(flow, warning):
    # OAuthlib has already validated the token response before raising its
    # scope-change warning. Never repeat the single-use code exchange.
    if not all(hasattr(warning, field) for field in ('token', 'new_scope', 'old_scope')):
        raise warning
    checked_scopes(flow.oauth2session.scope, warning.new_scope)
    flow.oauth2session.token = warning.token
    return flow.credentials


def failure_message(error):
    if isinstance(error, AuthorizationError):
        return str(error)
    # Never print arbitrary exception text: HTTP/OAuth errors can include codes,
    # callback URLs, client secrets or tokens.
    oauth_error = getattr(error, 'error', None)
    if oauth_error == 'invalid_grant':
        return 'The authorization code expired or was already used. Run the command again and use only its NEW link and redirect.'
    if oauth_error == 'access_denied':
        return 'Google consent was denied. Retry and approve the requested permissions.'
    if oauth_error in ('invalid_client', 'unauthorized_client', 'redirect_uri_mismatch'):
        return 'Google rejected the OAuth client configuration. Check the client JSON and its registered http://127.0.0.1:8765/ redirect URI.'
    if isinstance(error, (EOFError, KeyboardInterrupt)):
        return 'Authorization input was cancelled. Retry in an interactive terminal.'
    if isinstance(error, Warning):
        return 'Google returned different permissions. Retry and approve all requested access.'
    from google.auth.exceptions import RefreshError, TransportError
    if isinstance(error, RefreshError):
        # Google-auth stores the parsed response separately from its exception
        # text. Only known codes may leave this boundary; descriptions can echo
        # supplied credentials and are never displayed.
        response = next((arg for arg in error.args if isinstance(arg, dict)), {})
        code = response.get('error')
        if code == 'invalid_grant' and response.get('error_subtype') == 'invalid_rapt':
            code = 'invalid_rapt'
        messages = {
            'invalid_client': 'Google error: invalid_client. The client ID/secret was rejected. Use the same enabled secret in credentials.json and Playground.',
            'invalid_grant': 'Google error: invalid_grant. The refresh token is invalid, revoked or belongs to another client. Copy the complete Refresh token field from Playground Step 2; if needed authorize again with this project\'s own OAuth client.',
            'invalid_scope': 'Google error: invalid_scope. The refresh token does not support the requested scopes. Authorize all configured permissions again in Playground.',
            'unauthorized_client': 'Google error: unauthorized_client. This OAuth client is not authorized for the refresh flow. Check the web OAuth client configuration.',
            'invalid_request': 'Google error: invalid_request. Google rejected the refresh request. Check the local client configuration and copy only the refresh token value.',
            'invalid_rapt': 'Google error: invalid_rapt. Google requires reauthentication. Sign in and authorize again; Workspace session policy may require an administrator review.',
        }
        if isinstance(code, str) and code in messages:
            return messages[code]
        return 'Google rejected the refresh token. In Playground select Use your own OAuth credentials, use this project\'s client ID/secret, and generate a NEW refresh token.'
    if isinstance(error, TransportError):
        return 'Could not reach Google to verify the refresh token. Check network access and retry locally.'
    from requests.exceptions import RequestException
    if isinstance(error, RequestException):
        return 'Could not exchange the code with Google. Check network access and retry with a NEW authorization link.'
    return 'Authorization could not complete. Check the OAuth client JSON, token file permissions and configuration; no credentials were printed.'


def complete_pasted_redirect(flow, redirect_url, expected_state):
    """Exchange a private browser redirect without needing port forwarding."""
    parsed = urlparse(redirect_url.strip())
    query = parse_qs(parsed.query, keep_blank_values=True)
    if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.port != 8765 or
            parsed.path != '/' or parsed.username or parsed.password or parsed.fragment or
            len(query.get('state', [])) != 1 or
            not hmac.compare_digest(query['state'][0], expected_state)):
        raise AuthorizationError('Paste the FULL http://127.0.0.1:8765/ address after consent, from this command\'s NEW link. The Google consent-page URL or an older redirect will not work.')
    if 'error' in query:
        raise AuthorizationError('Google consent was denied or failed. Retry and approve all requested permissions with the intended account.')
    if len(query.get('code', [])) != 1 or not query['code'][0]:
        raise AuthorizationError('The redirect has no single authorization code. Finish consent and paste the full loopback address from this NEW session.')
    # Mirror the installed library's loopback callback implementation. The
    # registered redirect URI remains HTTP; only OAuthlib's parser uses HTTPS.
    response = 'https' + redirect_url.strip()[4:]
    try:
        flow.fetch_token(authorization_response=response, timeout=30)
    except Warning as warning:
        return recover_scope_change(flow, warning)
    return flow.credentials


def import_refresh_token(client_config, requested_scopes, refresh_token):
    """Verify a private Playground token; never infer grants from user input."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from requests import Session
    if not refresh_token.strip():
        raise AuthorizationError('No refresh token entered. Copy the refresh_token value from OAuth Playground Step 2 into this terminal only.')
    refresh_token = refresh_token.strip()
    if refresh_token.startswith('ya29.'):
        raise AuthorizationError('That is an ACCESS token. Copy the Refresh token field from Playground Step 2 instead.')
    if refresh_token.startswith('4/'):
        raise AuthorizationError('That is an authorization CODE. Exchange it in Playground Step 2, then copy the Refresh token field.')
    if refresh_token.startswith('GOCSPX-'):
        raise AuthorizationError('That is a CLIENT SECRET. Copy the Refresh token field from Playground Step 2 instead.')
    if any(character.isspace() for character in refresh_token) or any(character in refresh_token for character in ('"', "'", '{', '}')):
        raise AuthorizationError('Paste only the complete refresh token value, without quotes, JSON, spaces or line breaks. Copy it from the Refresh token field in Step 2.')
    refresh_scopes = list(requested_scopes)
    sheet_write = 'https://www.googleapis.com/auth/spreadsheets'
    sheet_read = 'https://www.googleapis.com/auth/spreadsheets.readonly'
    if sheet_write in refresh_scopes:
        refresh_scopes = [scope for scope in refresh_scopes if scope != sheet_read]
    creds = Credentials(None, refresh_token=refresh_token.strip(),
                        token_uri='https://oauth2.googleapis.com/token',
                        client_id=client_config['client_id'],
                        client_secret=client_config['client_secret'],
                        scopes=refresh_scopes)
    with Session() as session:
        creds.refresh(partial(Request(session=session), timeout=30))
    if not creds.token or creds.granted_scopes is None:
        raise AuthorizationError('Google did not return verified scope information. The existing token was preserved; authorize all configured permissions using your own OAuth client in Playground.')
    checked_scopes(requested_scopes, creds.granted_scopes)
    return creds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--paste-redirect', action='store_true', help='Complete consent from a remote workspace without a callback listener.')
    mode.add_argument('--paste-refresh-token', action='store_true', help='Privately import and verify a refresh token from Google OAuth Playground using your own client.')
    parser.add_argument('--account', help='Suggest the Google account to authorize; Google still requires sign-in and consent.')
    args = parser.parse_args()
    env = load_env()
    path = ROOT / env['GOOGLE_CREDENTIALS_FILE']
    if not path.exists() or path.is_symlink():
        raise SystemExit('Download OAuth client credentials.json into the project first.')
    os.chmod(path, 0o600)
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.oauth2.credentials import Credentials
    except ImportError:
        raise SystemExit('Install scripts/requirements-integrations.txt in a project virtual environment first.')
    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(path), env['GOOGLE_OAUTH_SCOPES'].split())
        consent_options = dict(access_type='offline', prompt='consent select_account', include_granted_scopes='true')
        if args.account:
            consent_options['login_hint'] = args.account
        # The URL carries no client secret or authorization token. Library opens
        # the official Google consent page; the callback binds loopback only.
        # Google can otherwise reuse a prior consent grant without returning a
        # refresh token.  A long-running trigger worker needs a refreshable
        # offline credential, not a short-lived access token.
        if args.paste_refresh_token:
            print('Use Google OAuth Playground with YOUR OWN configured OAuth client. Paste only its refresh_token value here; never send it in chat.', flush=True)
            refresh_token = getpass.getpass('Paste Playground refresh token (hidden): ')
            creds = import_refresh_token(flow.client_config, env['GOOGLE_OAUTH_SCOPES'].split(), refresh_token)
        elif args.paste_redirect:
            flow.redirect_uri = 'http://127.0.0.1:8765/'
            url, state = flow.authorization_url(**consent_options)
            print('Open this NEW link in your browser, select the intended account and approve ALL requested permissions, including Google Sheets editing:\n' + url, flush=True)
            print('After consent, the browser may show connection refused. Copy the FULL address-bar URL and paste it below. Do not send that URL in chat.', flush=True)
            redirect = getpass.getpass('Paste the full redirect URL (hidden): ')
            creds = complete_pasted_redirect(flow, redirect, state)
        else:
            try:
                creds = flow.run_local_server(host='127.0.0.1', port=8765, open_browser=True,
                                          authorization_prompt_message='Complete consent in your local browser.',
                                          success_message='Google callback received. Check your terminal for the final authorization result. You can close this tab.',
                                          **consent_options)
            except Warning as warning:
                creds = recover_scope_change(flow, warning)
        token = creds.to_json()
        # Validate the shape before replacing a previously working token. This
        # check uses no network and never prints credential fields.
        if not creds.refresh_token:
            raise AuthorizationError('Google did not provide offline access. Revoke this app\'s existing Google account grant, then retry and approve consent.')
        Credentials.from_authorized_user_info(json.loads(token))
        required_write = 'https://www.googleapis.com/auth/spreadsheets'
        actual_scopes = creds.granted_scopes if creds.granted_scopes is not None else creds.scopes
        granted = checked_scopes(env['GOOGLE_OAUTH_SCOPES'].split(), actual_scopes)
        # Persist actual grants so later readers do not infer consent from the
        # originally requested scopes.
        token_data = json.loads(token)
        token_data['scopes'] = sorted(granted)
        token = json.dumps(token_data)
        private_write(ROOT / env['GOOGLE_TOKEN_FILE'], token)
    except (Exception, KeyboardInterrupt) as error:
        raise SystemExit('Google authorization failed. ' + failure_message(error)) from None
    print('Google token saved securely. Google Sheets edit access: ' + ('granted' if required_write in granted else 'not requested') + '.')


if __name__ == '__main__':
    main()
