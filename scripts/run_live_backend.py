"""Start reusable live Sheets/model/Gmail providers for UI-created workflows."""
import argparse
import json
from pathlib import Path
import re
import smtplib
import ssl
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def check(env, sheet_resource, cell_range):
    from workflow_api.live_providers import model_configuration, registry_configuration, recipients
    from runtime.connectors import GoogleSheetsConnector
    from openai import OpenAI
    config = registry_configuration(env)
    model, _, _ = model_configuration(env)
    errors = 0
    try:
        client = OpenAI(api_key=env['OPENAI_API_KEY'], base_url=env.get('OPENAI_BASE_URL'), max_retries=0, timeout=20)
        if model not in {item.id for item in client.models.list()}:
            raise ValueError()
        print('Model access: PASS (' + model + ')')
    except Exception:
        print('Model access: FAILED. Check the configured model and API account.')
        errors += 1
    try:
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=20) as smtp:
            smtp.ehlo(); smtp.starttls(context=ssl.create_default_context()); smtp.ehlo()
            smtp.login(env['GMAIL_SMTP_USER'], env['GMAIL_SMTP_PASSWORD']); smtp.noop()
        print('Gmail STARTTLS/AUTH: PASS (no email sent)')
    except Exception:
        print('Gmail authentication: FAILED. Check the saved Gmail app password.')
        errors += 1
    if sheet_resource:
        match = re.fullmatch(r'https://docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]+)(?:/.*)?', sheet_resource)
        sheet_id = match.group(1) if match else sheet_resource
        if not re.fullmatch(r'[A-Za-z0-9_-]{20,}', sheet_id):
            raise ValueError('Use a Google spreadsheet URL or ID.')
        definition = next(item['definition'] for item in config['tools'] if item['definition']['tool_id'] == 'google_sheets_read_rows')
        # Diagnostic read only; not an execution grant and never persisted.
        grant = {**definition, 'authorization_state': 'authorized', 'authorization_reference': 'operator_read_check', 'credential_reference': 'cred_google_sheets'}
        connector = GoogleSheetsConnector(lambda reference: {'provider_id': 'google_sheets'}, ROOT / env['GOOGLE_TOKEN_FILE'], timeout=20)
        try:
            output = connector.invoke(grant, {'spreadsheet_id': sheet_id, 'range': cell_range}, 'operator_check')
            print('Sheet access: PASS; headers: ' + json.dumps(output['rows'][0] if output['rows'] else []))
            print('Existing data rows:', max(0, len(output['rows']) - 1))
        except Exception as exc:
            print('Sheet access: FAILED (' + str(getattr(exc, 'code', 'SHEETS_READ_FAILED')) + '). Check Google authorization, sharing and tab/range.')
            errors += 1
    print('Approved email recipients: ' + ', '.join(recipients(env)))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--check', action='store_true', help='Read-only connection checks; sends no email.')
    parser.add_argument('--sheet', help='Spreadsheet URL or ID for a read-only check.')
    parser.add_argument('--range', default='A:K', help='A1 range, optionally including the tab name.')
    args = parser.parse_args()
    from workflow_api.live_providers import environment, create_configured_app
    env = environment()
    try:
        if args.check:
            raise SystemExit(1 if check(env, args.sheet, args.range) else 0)
        app = create_configured_app(env)
    except ValueError:
        raise SystemExit('Provider configuration is incomplete or invalid. See docs/sheets-gmail.md and run --check.') from None
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=args.port)


if __name__ == '__main__':
    main()
