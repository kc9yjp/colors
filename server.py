#!/usr/bin/env python3
import http.client
import http.server
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATA_FILE = Path('/data/palettes.json')
STATIC_FILE = Path('/app/index.html')
MAX_PALETTES = int(os.environ.get('MAX_PALETTES', 20))
OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'host.docker.internal')
OLLAMA_PORT = int(os.environ.get('OLLAMA_PORT', 11434))
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'smollm2:latest')


def load_palettes():
    try:
        return json.loads(DATA_FILE.read_text())
    except Exception:
        return []


def save_palettes(palettes):
    tmp = DATA_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps(palettes, indent=2))
    os.replace(tmp, DATA_FILE)





class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send_json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(length))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        try:
            if self.path in ('/', '/index.html'):
                body = STATIC_FILE.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path == '/api/palettes':
                self.send_json(200, load_palettes())

            else:
                self.send_json(404, {'error': 'not found'})
        except Exception as e:
            self.send_json(500, {'error': str(e)})

    def do_POST(self):
        try:
            if self.path == '/api/palettes':
                body = self.read_body()
                keyword = str(body.get('keyword', '')).strip()
                colors = body.get('colors', [])
                if not keyword:
                    return self.send_json(400, {'error': 'keyword required'})
                if not isinstance(colors, list) or not colors:
                    return self.send_json(400, {'error': 'colors required'})

                record = {
                    'id': str(uuid.uuid4()),
                    'keyword': keyword,
                    'colors': colors,
                    'saved_at': datetime.now(timezone.utc).isoformat(),
                }
                palettes = load_palettes()
                palettes.append(record)
                max_p = MAX_PALETTES
                if len(palettes) > max_p:
                    palettes = palettes[-max_p:]  # FIFO: drop oldest
                save_palettes(palettes)
                self.send_json(201, record)



            elif self.path == '/api/suggest':
                body = self.read_body()
                prompt = str(body.get('prompt', '')).strip()
                if not prompt:
                    return self.send_json(400, {'error': 'prompt required'})

                model = OLLAMA_MODEL
                system = (
                    'You are a color palette generator. Given a mood or description, '
                    'respond ONLY with valid JSON: {"colors": ["#rrggbb", ...]} '
                    'where you return 5-7 hex color codes that match the mood. '
                    'No explanation, no markdown, just the JSON.'
                )
                req_body = json.dumps({
                    'model': model,
                    'messages': [
                        {'role': 'system', 'content': system},
                        {'role': 'user', 'content': f'Generate a color palette for: {prompt}'},
                    ],
                    'stream': False,
                }).encode()

                try:
                    conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=30)
                    conn.request('POST', '/api/chat', req_body, {
                        'Content-Type': 'application/json',
                        'Content-Length': str(len(req_body)),
                    })
                    resp = conn.getresponse()
                    if resp.status != 200:
                        return self.send_json(502, {'error': f'Ollama error: {resp.read().decode()}'})
                    data = json.loads(resp.read().decode())
                    conn.close()
                    content = data.get('message', {}).get('content', '')
                    match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                    if match:
                        result = json.loads(match.group())
                        colors = result.get('colors', [])
                        if colors:
                            return self.send_json(200, {'colors': colors})
                    return self.send_json(200, {'colors': []})
                except Exception as e:
                    return self.send_json(502, {'error': f'Connection failed: {str(e)}'})

            else:
                self.send_json(404, {'error': 'not found'})
        except Exception as e:
            self.send_json(500, {'error': str(e)})

    def do_DELETE(self):
        try:
            m = re.fullmatch(r'/api/palettes/([^/]+)', self.path)
            if not m:
                return self.send_json(404, {'error': 'not found'})
            pid = m.group(1)
            palettes = load_palettes()
            updated = [p for p in palettes if p.get('id') != pid]
            if len(updated) == len(palettes):
                return self.send_json(404, {'error': 'palette not found'})
            save_palettes(updated)
            self.send_json(200, {'ok': True})
        except Exception as e:
            self.send_json(500, {'error': str(e)})


if __name__ == '__main__':
    os.makedirs('/data', exist_ok=True)
    port = int(os.environ.get('PORT', 80))
    server = http.server.HTTPServer(('', port), Handler)
    print(f'Serving on port {port}')
    server.serve_forever()
