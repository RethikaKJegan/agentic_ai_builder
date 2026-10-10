"""Loopback-only POC webhook: signed payloads, no external actions."""
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from integration_config import load_env


def signature(secret, body):
    return 'sha256=' + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def make_server(secret, port=0):
    if len(secret) < 32:
        raise ValueError('Webhook secret is missing or too short')

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            self.connection.settimeout(5)
            try:
                size = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                self.send_error(400)
                return
            if self.path != '/webhook' or not 0 < size <= 65536:
                self.send_error(400)
                return
            body = self.rfile.read(size)
            valid = hmac.compare_digest(self.headers.get('X-Webhook-Signature', ''), signature(secret, body))
            self.send_response(200 if valid else 401)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"accepted":true}' if valid else b'{"accepted":false}')

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


if __name__ == '__main__':
    env = load_env()
    server = make_server(env['WEBHOOK_SECRET'], int(env.get('WEBHOOK_PORT', '8787')))
    print('Local webhook listening on loopback only. Press Ctrl-C to stop.')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
