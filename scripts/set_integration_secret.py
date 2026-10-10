"""Enter credentials at a local terminal, with input echo disabled."""
import getpass
import sys
import warnings
from integration_config import save_value

ALLOWED = {'SLACK_APP_TOKEN', 'SLACK_USER_TOKEN', 'SLACK_BOT_TOKEN', 'SLACK_SIGNING_SECRET', 'GITHUB_TOKEN', 'GMAIL_SMTP_USER', 'GMAIL_SMTP_PASSWORD',
           'BREVO_SMTP_USER', 'BREVO_SMTP_PASSWORD', 'SLACK_WEBHOOK_URL',
           'GOOGLE_SHEETS_SPREADSHEET_ID', 'GOOGLE_DOCS_DOCUMENT_ID',
           'GOOGLE_CALENDAR_ID', 'GITHUB_TEST_REPOSITORY'}

if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ALLOWED:
        raise SystemExit('Supply one supported integration variable name; never a value as an argument.')
    if not sys.stdin.isatty():
        raise SystemExit('Run locally in an interactive terminal for hidden input.')
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        secret = getpass.getpass('Value (hidden): ')
    if not secret:
        raise SystemExit('Empty value; nothing saved.')
    save_value(sys.argv[1], secret)
    print('Saved securely to the project .env.')
