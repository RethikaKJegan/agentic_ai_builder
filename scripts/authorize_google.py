"""Authorize configured Google permissions in your own browser."""
import json
import argparse
import getpass
import hmac
import os
import sys
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paste-redirect', action='store_true', help='Complete consent from a remote workspace without a callback listener.')
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
        if args.paste_redirect:
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
                                          success_message='Authorization saved locally. You can close this tab.',
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
