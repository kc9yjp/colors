#!/usr/bin/env python3
import http.server
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATA_FILE = Path('/data/palettes.json')
CONFIG_FILE = Path('/data/config.json')
STATIC_FILE = Path('/app/index.html')
DEFAULT_MAX = 20


def load_palettes():
    try:
        return json.loads(DATA_FILE.read_text())
    except Exception:
        return []


def save_palettes(palettes):
    tmp = DATA_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps(palettes, indent=2))
    os.replace(tmp, DATA_FILE)


def load_config():
    try:
        return json.loads(CONFIG_FILE.read_text())
    except Exception:
        return {'max_palettes': DEFAULT_MAX}


def save_config(cfg):
    tmp = CONFIG_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps(cfg, indent=2))
    os.replace(tmp, CONFIG_FILE)


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
            elif self.path == '/api/config':
                self.send_json(200, load_config())
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
                max_p = load_config().get('max_palettes', DEFAULT_MAX)
                if len(palettes) > max_p:
                    palettes = palettes[-max_p:]  # FIFO: drop oldest
                save_palettes(palettes)
                self.send_json(201, record)

            elif self.path == '/api/config':
                body = self.read_body()
                max_p = int(body.get('max_palettes', DEFAULT_MAX))
                if max_p < 1:
                    return self.send_json(400, {'error': 'max_palettes must be >= 1'})
                cfg = {'max_palettes': max_p}
                save_config(cfg)
                self.send_json(200, cfg)

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
