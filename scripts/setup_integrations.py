"""Idempotent local setup. Existing values are retained; secrets never printed."""
import json
import os
import secrets
from integration_config import ROOT, load_env, private_write

DEFAULTS = {
    'OPEN_METEO_BASE_URL': 'https://api.open-meteo.com',
    'OPEN_METEO_LATITUDE': '13.0827',
    'OPEN_METEO_LONGITUDE': '80.2707',
    'OPEN_LIBRARY_BASE_URL': 'https://openlibrary.org',
    'REST_API_BASE_URL': 'https://jsonplaceholder.typicode.com',
    'REST_API_AUTH_MODE': 'none',
    'GITHUB_API_BASE_URL': 'https://api.github.com',
    'GITHUB_TOKEN': '',
    'GITHUB_TEST_REPOSITORY': '',
    'SLACK_WEBHOOK_URL': '',
    'GMAIL_SMTP_HOST': 'smtp.gmail.com',
    'GMAIL_SMTP_PORT': '587',
    'GMAIL_SMTP_USER': '',
    'GMAIL_SMTP_PASSWORD': '',
    'BREVO_SMTP_HOST': 'smtp-relay.brevo.com',
    'BREVO_SMTP_PORT': '587',
    'BREVO_SMTP_USER': '',
    'BREVO_SMTP_PASSWORD': '',
    'GOOGLE_CLOUD_PROJECT_ID': '',
    'GOOGLE_CREDENTIALS_FILE': 'credentials.json',
    'GOOGLE_TOKEN_FILE': 'token.json',
    'GOOGLE_OAUTH_SCOPES': ' '.join('https://www.googleapis.com/auth/' + scope for scope in [
        'spreadsheets.readonly', 'drive.metadata.readonly', 'calendar.events.readonly', 'documents.readonly']),
    'GOOGLE_SHEETS_SPREADSHEET_ID': '',
    'GOOGLE_DOCS_DOCUMENT_ID': '',
    'GOOGLE_CALENDAR_ID': 'primary',
    'WEBHOOK_HOST': '127.0.0.1',
    'WEBHOOK_PORT': '8787',
    'WEBHOOK_PATH': '/webhook',
    'WEBHOOK_SECRET': '',
}


def main():
    path = ROOT / '.env'
    if path.is_symlink():
        raise SystemExit('Refusing a symlink .env.')
    old = path.read_text() if path.exists() else ''
    values = load_env() if path.exists() else {}
    missing = {key: value for key, value in DEFAULTS.items() if key not in values}
    if 'WEBHOOK_SECRET' not in values or not values['WEBHOOK_SECRET']:
        generated = secrets.token_hex(32)
        if 'WEBHOOK_SECRET' in values:
            from integration_config import save_value
            save_value('WEBHOOK_SECRET', generated)
            old = path.read_text()
        else:
            missing['WEBHOOK_SECRET'] = generated
    if missing:
        contents = old.rstrip('\n') + '\n\n# Real tool integrations (project-local)\n'
        contents += '\n'.join(key + '=' + json.dumps(value) for key, value in missing.items()) + '\n'
        private_write(path, contents)
    else:
        os.chmod(path, 0o600)
    ignore = ROOT / '.gitignore'
    contents = ignore.read_text() if ignore.exists() else ''
    for name in ['.env', '.env.*', '!.env.example', 'credentials.json', 'token.json', '.integration-*', '.venv-integrations/']:
        if name not in contents.splitlines():
            contents = contents.rstrip('\n') + '\n' + name + '\n'
    ignore.write_text(contents)
    for name in ['credentials.json', 'token.json']:
        p = ROOT / name
        if p.exists() and not p.is_symlink():
            os.chmod(p, 0o600)
    # Only keys are reused from the existing example. Its values are replaced.
    example = ROOT / '.env.example'
    existing_keys = []
    if example.exists():
        for line in example.read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                existing_keys.append(line.split('=', 1)[0].strip())
    keys = list(dict.fromkeys(existing_keys + list(DEFAULTS)))
    example.write_text('# Placeholders only; real values belong in the ignored .env.\n' +
                       '\n'.join(key + '=REPLACE_ME' for key in keys) + '\n')
    print('Project-local integration settings prepared; existing values preserved. No secrets logged.')


if __name__ == '__main__':
    main()
