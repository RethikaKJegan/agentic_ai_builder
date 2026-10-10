"""Safe read-only checks. Never emit provider bodies, URLs, or credentials."""
import json
import smtplib
import ssl
import threading
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from integration_config import ROOT, load_env, private_write
from local_webhook import make_server, signature


def fetch(url, token=None, data=None, headers=None):
    request_headers = {'Accept': 'application/json', 'User-Agent': 'AgenticAIBuilder-POC/1.0'}
    request_headers.update(headers or {})
    if token:
        request_headers['Authorization'] = 'Bearer ' + token
    with urlopen(Request(url, data=data, headers=request_headers), timeout=20) as response:
        if response.status != 200:
            raise ValueError('Unexpected response status')
        return json.load(response)


def require(condition):
    if not condition:
        raise ValueError('Unexpected response shape')


def main():
    env = load_env()
    results = []

    def record(name, status, detail):
        results.append({'integration': name, 'status': status, 'detail': detail})
        print(name + ': ' + status + ' — ' + detail)

    def check(name, operation, detail):
        try:
            operation()
            record(name, 'verified', detail)
        except HTTPError as exc:
            record(name, 'failed', 'HTTP ' + str(exc.code) + '; response details suppressed.')
        except smtplib.SMTPAuthenticationError:
            record(name, 'failed', 'SMTP authentication rejected; response details suppressed.')
        except Exception as exc:
            record(name, 'failed', type(exc).__name__ + '; sensitive error details suppressed.')

    def weather():
        data = fetch(env['OPEN_METEO_BASE_URL'] + '/v1/forecast?' + urlencode({
            'latitude': env['OPEN_METEO_LATITUDE'], 'longitude': env['OPEN_METEO_LONGITUDE'],
            'current': 'temperature_2m', 'forecast_days': 1}))
        require(isinstance(data.get('current', {}).get('temperature_2m'), (int, float)))

    check('Open-Meteo API', weather, 'GET forecast returned a numeric current temperature.')
    check('Open Library API', lambda: require(fetch(env['OPEN_LIBRARY_BASE_URL'] +
          '/search.json?q=pride+and+prejudice&limit=1').get('numFound', 0) > 0),
          'GET search returned matching books.')
    check('Generic REST API Connector', lambda: require(fetch(env['REST_API_BASE_URL'] +
          '/posts/1').get('id') == 1), 'JSONPlaceholder GET /posts/1 returned the expected record.')

    if env.get('GITHUB_TOKEN'):
        def github():
            require(bool(fetch('https://api.github.com/user', env['GITHUB_TOKEN']).get('login')))
            repo = env.get('GITHUB_TEST_REPOSITORY')
            if repo:
                require('full_name' in fetch('https://api.github.com/repos/' +
                        quote(repo, safe='/'), env['GITHUB_TOKEN']))
        check('GitHub REST API', github, 'Authenticated GET /user verified' +
              ('; configured repository metadata access verified.' if env.get('GITHUB_TEST_REPOSITORY')
               else '; private repository permissions not tested.'))
    else:
        record('GitHub REST API', 'requires_setup', 'Create a minimally scoped fine-grained token and save GITHUB_TOKEN locally.')

    record('Slack Incoming Webhooks', 'requires_approval' if env.get('SLACK_WEBHOOK_URL') else 'requires_setup',
           'No message posted. An authenticated webhook test requires approval to post.' if env.get('SLACK_WEBHOOK_URL')
           else 'Create/authorize an incoming webhook for one test channel; save its URL locally.')

    for prefix, name in [('GMAIL', 'Gmail SMTP'), ('BREVO', 'Brevo SMTP')]:
        if not env.get(prefix + '_SMTP_USER') or not env.get(prefix + '_SMTP_PASSWORD'):
            record(name, 'requires_setup', 'SMTP username and app password/SMTP key are missing.')
            continue
        def smtp(prefix=prefix):
            with smtplib.SMTP(env[prefix + '_SMTP_HOST'], int(env[prefix + '_SMTP_PORT']), timeout=20) as client:
                client.ehlo()
                client.starttls(context=ssl.create_default_context())
                client.ehlo()
                client.login(env[prefix + '_SMTP_USER'], env[prefix + '_SMTP_PASSWORD'])
                require(client.noop()[0] == 250)
        check(name, smtp, 'STARTTLS, AUTH, and NOOP verified. No email sent; delivery untested.')

    google_names = ['Google Sheets API', 'Google Drive API', 'Google Calendar API', 'Google Docs API']
    token_path = ROOT / env['GOOGLE_TOKEN_FILE']
    if not token_path.exists():
        for name in google_names:
            record(name, 'requires_setup', 'One shared Google OAuth client and user authorization are required.')
    else:
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request as GoogleRequest
            creds = Credentials.from_authorized_user_file(str(token_path))
            if not creds.valid:
                creds.refresh(GoogleRequest())
                private_write(token_path, creds.to_json())
            token = creds.token
            if not token:
                raise ValueError('Missing access token')
        except Exception as exc:
            for name in google_names:
                record(name, 'requires_setup', 'Google token unavailable/refresh failed: ' + type(exc).__name__ + '.')
        else:
            for name, key, endpoint in [
                ('Google Sheets API', 'GOOGLE_SHEETS_SPREADSHEET_ID', 'https://sheets.googleapis.com/v4/spreadsheets/'),
                ('Google Docs API', 'GOOGLE_DOCS_DOCUMENT_ID', 'https://docs.googleapis.com/v1/documents/')]:
                if env.get(key):
                    check(name, lambda key=key, endpoint=endpoint: require(isinstance(
                        fetch(endpoint + quote(env[key], safe=''), token), dict)),
                        'Authenticated read of the configured resource succeeded; writes untested.')
                else:
                    record(name, 'requires_setup', 'Set ' + key + ' to a resource you can read.')
            check('Google Drive API', lambda: require('files' in fetch(
                  'https://www.googleapis.com/drive/v3/files?pageSize=1&fields=files(id)', token)),
                  'Authenticated files.list succeeded; writes untested.')
            check('Google Calendar API', lambda: require('kind' in fetch(
                  'https://www.googleapis.com/calendar/v3/calendars/' +
                  quote(env['GOOGLE_CALENDAR_ID'], safe='') + '/events?maxResults=1', token)),
                  'Authenticated events.list succeeded; no event created.')

    def webhook():
        secret = env['WEBHOOK_SECRET']
        require(len(secret) >= 64)
        server = make_server(secret)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        body = b'{"event":"local-validation"}'
        url = 'http://127.0.0.1:' + str(server.server_port) + '/webhook'
        try:
            require(fetch(url, data=body, headers={'X-Webhook-Signature': signature(secret, body)}).get('accepted') is True)
            for bad_body, bad_signature in [(body, 'sha256=invalid'), (body + b' ', signature(secret, body))]:
                try:
                    fetch(url, data=bad_body, headers={'X-Webhook-Signature': bad_signature})
                except HTTPError as exc:
                    require(exc.code == 401)
                else:
                    raise ValueError('Invalid signature accepted')
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
    check('Webhook Connector', webhook, 'Local loopback POST accepted a valid HMAC and rejected invalid/tampered payloads. No external registration.')

    report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'results': results,
              'limitations': ['Configuration and smoke checks only; registry/runtime wiring is not implemented.',
                              'No emails, Slack messages, calendar events, billing, or external webhook registration.',
                              'Local webhook is a POC receiver without replay protection; not exposed publicly.']}
    (ROOT / 'docs/integration-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    lines = ['# Integration validation report', '', 'Checked (UTC): ' + report['checked_at_utc'], '',
             '| Integration | Status | Evidence / remaining setup |', '| --- | --- | --- |']
    lines.extend('| ' + row['integration'] + ' | ' + row['status'] + ' | ' + row['detail'] + ' |' for row in results)
    lines.extend(['', '## Limits', ''] + ['- ' + item for item in report['limitations']])
    (ROOT / 'docs/integration-validation.md').write_text('\n'.join(lines) + '\n')
    return 1 if any(row['status'] == 'failed' for row in results) else 0


if __name__ == '__main__':
    raise SystemExit(main())
