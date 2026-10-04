import json
import os
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

# Configure before importing the app: no real Groq key, so startup makes no network calls
os.environ['GROQ_API_KEY'] = ''
os.environ['SECRET_KEY'] = 'test-secret'
os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402


class FakeGroqHandler(BaseHTTPRequestHandler):
    """OpenAI-compatible chat completions endpoint that streams like Groq (chunked SSE)"""
    protocol_version = 'HTTP/1.1'
    tokens = ['Statins ', 'reduce ', 'LDL ', '≥30%.']
    delay = 0.0
    fail_after = None  # drop the connection after this many tokens
    chunked = True  # False: HTTP/1.0 style body delimited by connection close

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if not body.get('stream'):
            out = json.dumps({'choices': [{'message': {'content': 'ok'}}]}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(out)))
            self.end_headers()
            self.wfile.write(out)
            return
        if not self.chunked:
            self.protocol_version = 'HTTP/1.0'
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')  # no charset, like real SSE
        if self.chunked:
            self.send_header('Transfer-Encoding', 'chunked')
        self.end_headers()
        try:
            for i, token in enumerate(self.tokens):
                if self.fail_after is not None and i == self.fail_after:
                    # Abort mid-response; shutdown() really drops the TCP connection
                    self.connection.shutdown(socket.SHUT_RDWR)
                    return
                event = {'choices': [{'delta': {'content': token}}]}
                self._chunk(f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode('utf-8'))
                time.sleep(self.delay)
            self._chunk(b'data: [DONE]\n\n')
            if self.chunked:
                self.wfile.write(b'0\r\n\r\n')
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass  # client cancelled the stream

    def _chunk(self, data: bytes):
        if self.chunked:
            data = f'{len(data):x}\r\n'.encode() + data + b'\r\n'
        self.wfile.write(data)
        self.wfile.flush()

    def log_message(self, *args):
        pass


@pytest.fixture(scope='session')
def fake_groq():
    server = ThreadingHTTPServer(('127.0.0.1', 0), FakeGroqHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_address[1]}'
    server.shutdown()


@pytest.fixture
def app_mod(monkeypatch):
    app_module.limiter.reset()
    FakeGroqHandler.tokens = ['Statins ', 'reduce ', 'LDL ', '≥30%.']
    FakeGroqHandler.delay = 0.0
    FakeGroqHandler.fail_after = None
    FakeGroqHandler.chunked = True
    # Never hit the real PubMed from tests
    monkeypatch.setattr(app_module.literature_service, '_search_pubmed',
                        lambda *a, **k: app_module.literature_service._get_fallback_studies(*a, **k))
    return app_module


@pytest.fixture
def client(app_mod):
    return app_mod.app.test_client()


@pytest.fixture
def token(client):
    resp = client.post('/auth/login', json={'username': 'demo_provider', 'password': 'demo123'})
    assert resp.status_code == 200
    return resp.get_json()['access_token']


@pytest.fixture
def groq_enabled(app_mod, fake_groq, monkeypatch):
    """Point the app at the fake Groq server"""
    monkeypatch.setitem(app_mod.app.config, 'GROQ_API_KEY', 'test-key')
    monkeypatch.setitem(app_mod.app.config, 'GROQ_API_BASE', fake_groq)
    monkeypatch.setattr(app_mod.ai_service, 'groq_available', True)
    return FakeGroqHandler
