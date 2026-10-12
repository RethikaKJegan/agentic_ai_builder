"""Remote OAuth completion retains state checks and keeps codes out of logs."""
import runpy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from scripts import integration_config


class GoogleRedirectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.dict('sys.modules', {'integration_config': integration_config}):
            cls.module = runpy.run_path(str(integration_config.ROOT / 'scripts/authorize_google.py'))
            cls.complete = staticmethod(cls.module['complete_pasted_redirect'])

    def test_matching_loopback_redirect_is_exchanged_without_callback_server(self):
        flow = SimpleNamespace(fetch_token=Mock(), credentials=object())
        result = self.complete(flow, 'http://127.0.0.1:8765/?state=expected&code=offline-code', 'expected')
        self.assertIs(result, flow.credentials)
        flow.fetch_token.assert_called_once_with(authorization_response='https://127.0.0.1:8765/?state=expected&code=offline-code', timeout=30)

    def test_wrong_state_host_and_duplicate_code_do_not_reach_google(self):
        for url in ('http://127.0.0.1:8765/?state=wrong&code=x', 'http://evil.example:8765/?state=expected&code=x',
                    'http://127.0.0.1:8765/?state=expected&code=x&code=y'):
            flow = SimpleNamespace(fetch_token=Mock(), credentials=object())
            with self.assertRaises(ValueError):
                self.complete(flow, url, 'expected')
            flow.fetch_token.assert_not_called()

    def test_consent_url_empty_code_and_denial_never_reach_exchange(self):
        for url in ('https://accounts.google.com/signin/oauth/consent',
                    'http://127.0.0.1:8765/?state=expected&code=',
                    'http://127.0.0.1:8765/?state=expected&error=access_denied'):
            flow = SimpleNamespace(fetch_token=Mock(), credentials=object())
            with self.assertRaises(ValueError):
                self.complete(flow, url, 'expected')
            flow.fetch_token.assert_not_called()

    def test_real_oauth_scope_change_accepts_covered_grants_and_rejects_missing(self):
        from google_auth_oauthlib.flow import InstalledAppFlow
        from requests import Response, Request
        read = 'https://www.googleapis.com/auth/spreadsheets.readonly'
        write = 'https://www.googleapis.com/auth/spreadsheets'
        for scopes, accepted in ((write + ' extra', True), (read, False)):
            flow = InstalledAppFlow.from_client_config({'installed': {
                'client_id': 'test-client', 'client_secret': 'private-secret',
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token'}}, [read, write])
            flow.redirect_uri = 'http://127.0.0.1:8765/'
            _, state = flow.authorization_url()
            response = Response()
            response.status_code = 200
            response.request = Request('POST', 'https://oauth2.googleapis.com/token', data='test').prepare()
            response._content = json.dumps({'access_token': 'private-access',
                'refresh_token': 'private-refresh', 'token_type': 'Bearer',
                'expires_in': 3600, 'scope': scopes}).encode()
            with patch.dict('os.environ', {}, clear=True), patch.object(flow.oauth2session, 'request', return_value=response) as post:
                if accepted:
                    creds = self.complete(flow, 'http://127.0.0.1:8765/?state=' + state + '&code=private-code', state)
                    self.assertIn(write, creds.granted_scopes)
                else:
                    with self.assertRaisesRegex(ValueError, 'permissions were not granted'):
                        self.complete(flow, 'http://127.0.0.1:8765/?state=' + state + '&code=private-code', state)
                self.assertEqual(post.call_count, 1)

    def test_failure_messages_never_echo_secrets(self):
        from oauthlib.oauth2 import InvalidGrantError
        from requests.exceptions import ConnectionError
        for error in (ValueError('private-secret'), Warning('private-secret'),
                      InvalidGrantError(description='private-secret'),
                      ConnectionError('private-secret')):
            self.assertNotIn('private-secret', self.module['failure_message'](error))
        self.assertIn('NEW link', self.module['failure_message'](InvalidGrantError()))

    def test_incomplete_grants_preserve_existing_token(self):
        self.check_token_save(['read'], 'permissions were not granted')

    def test_success_saves_actual_grants_privately(self):
        self.check_token_save(['read', 'write', 'extra'], None)

    def test_missing_offline_access_preserves_existing_token(self):
        self.check_token_save(['read', 'write'], 'offline access', refresh_token=None)

    def check_token_save(self, grants, error, refresh_token='private-refresh'):
        from google.oauth2.credentials import Credentials
        creds = Credentials('private-access', refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token', client_id='test',
            client_secret='private-secret', scopes=['read', 'write'], granted_scopes=grants)
        flow = Mock()
        flow.authorization_url.return_value = ('https://accounts.google.com/test', 'expected')
        main = self.module['main']
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'credentials.json').write_text('{}')
            (root / 'token.json').write_text('existing-token')
            env = {'GOOGLE_CREDENTIALS_FILE': 'credentials.json',
                   'GOOGLE_TOKEN_FILE': 'token.json', 'GOOGLE_OAUTH_SCOPES': 'read write'}
            with patch.dict(main.__globals__, {'ROOT': root, 'load_env': lambda: env,
                       'complete_pasted_redirect': lambda *args: creds,
                       'getpass': SimpleNamespace(getpass=Mock(return_value='private-redirect'))}), \
                 patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file', return_value=flow), \
                 patch('sys.argv', ['authorize_google.py', '--paste-redirect', '--account', 'test@example.com']), \
                 patch('builtins.print'):
                if error:
                    with self.assertRaisesRegex(SystemExit, error):
                        main()
                else:
                    main()
            if error:
                self.assertEqual((root / 'token.json').read_text(), 'existing-token')
            else:
                self.assertEqual(json.loads((root / 'token.json').read_text())['scopes'], sorted(grants))
                self.assertEqual((root / 'token.json').stat().st_mode & 0o777, 0o600)
            self.assertEqual(flow.authorization_url.call_args.kwargs['login_hint'], 'test@example.com')
            self.assertIn('select_account', flow.authorization_url.call_args.kwargs['prompt'])
