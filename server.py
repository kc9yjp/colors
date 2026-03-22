#!/usr/bin/env python3
import http.client
import http.server
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urljoin

logging.basicConfig(level=os.environ.get('LOG_LEVEL', 'INFO'), format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

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
def fetch_url(url, base_scheme='https'):
    for _ in range(10):
        parsed = urlparse(url)
        if not parsed.scheme:
            url = base_scheme + '://' + url
            parsed = urlparse(url)
        if not parsed.netloc:
            raise ValueError('Invalid URL')
        host = parsed.netloc
        path = parsed.path or '/'
        if parsed.query:
            path += '?' + parsed.query
        port = 443 if parsed.scheme == 'https' else 80
        if ':' in host:
            host, port_str = host.rsplit(':', 1)
            port = int(port_str)
        conn = http.client.HTTPSConnection(host, port, timeout=15) if parsed.scheme == 'https' else http.client.HTTPConnection(host, port, timeout=15)
        try:
            conn.request('GET', path, headers={'User-Agent': 'Mozilla/5.0 (compatible; DevPalette/1.0)'})
            resp = conn.getresponse()
            if resp.status in (301, 302, 303, 307, 308):
                location = resp.getheader('Location')
                if location:
                    logger.info(f'Following redirect: {url} -> {location}')
                    url = location
                    base_scheme = parsed.scheme
                    continue
                raise Exception(f'Redirect without Location header for {url}')
            if resp.status in (401, 403, 406, 429):
                logger.warning(f'[BLOCKED?] {url} returned HTTP {resp.status}')
                raise Exception(f'HTTP {resp.status} (Likely blocked) for {url}')
            
            if resp.status != 200:
                logger.error(f'Failed to fetch {url}: HTTP {resp.status}')
                raise Exception(f'HTTP {resp.status} for {url}')
            content = resp.read().decode('utf-8', errors='ignore')
            
            lower_content = content.lower()
            if "cloudflare" in lower_content and ("attention required" in lower_content or "just a moment..." in lower_content):
                logger.warning(f'[BLOCKED?] {url} returned Cloudflare challenge')
            elif "aws-waf" in lower_content or ("request blocked" in lower_content and "cloud" in lower_content) or ("403 error" in lower_content and "amazon" in lower_content) or "aws web application firewall" in lower_content:
                logger.warning(f'[BLOCKED?] {url} returned AWS WAF block')
            elif "enable javascript and cookies to continue" in lower_content or "please verify you are a human" in lower_content:
                logger.warning(f'[BLOCKED?] {url} returned generic bot challenge')
                
        except (TimeoutError, ConnectionRefusedError, ConnectionResetError) as e:
            logger.warning(f'[BLOCKED/UNREACHABLE?] {url} connection failed: {e}')
            raise Exception(f"Connection Error: {e} for {url}")
        finally:
            conn.close()
        logger.info(f'Fetched {url} ({len(content)} bytes)')
        return content, f'{parsed.scheme}://{parsed.netloc}'
    raise Exception(f'Too many redirects for {url}')


def fetch_linked_resources(html, base_url, progress_cb=None):
    css_links = re.findall(r'<link[^>]+href=["\']([^"\']+)["\'][^>]*>', html, re.IGNORECASE)
    js_links = re.findall(r'<script[^>]+src=["\']([^"\']+)["\'][^>]*>', html, re.IGNORECASE)
    
    logger.info(f'Found {len(css_links)} CSS links and {len(js_links)} JS links')
    
    content = html
    base_scheme = 'https'
    fetched = 0
    
    for href in css_links[:10]:
        absolute_href = urljoin(base_url, href)
        filename = absolute_href.split('/')[-1][:40]
        if progress_cb:
            progress_cb(f'Scanning {filename}…')
        try:
            css_content, _ = fetch_url(absolute_href, base_scheme)
            content += '\n' + css_content
            fetched += 1
        except Exception as e:
            logger.warning(f'Failed to fetch CSS {absolute_href}: {e}')
    
    for src in js_links[:10]:
        absolute_src = urljoin(base_url, src)
        filename = absolute_src.split('/')[-1][:40]
        if progress_cb:
            progress_cb(f'Scanning {filename}…')
        try:
            js_content, _ = fetch_url(absolute_src, base_scheme)
            content += '\n' + js_content
            fetched += 1
        except Exception as e:
            logger.warning(f'Failed to fetch JS {absolute_src}: {e}')
    
    logger.info(f'Processed {fetched} linked resources, total content: {len(content)} bytes')
    
    if progress_cb:
        progress_cb('Extracting colors…')
    
    return content


def extract_colors(html):
    hex_pattern = re.compile(r'#(?:[0-9a-fA-F]{3}){1,2}(?![0-9a-fA-F])')
    rgb_pattern = re.compile(r'rgb\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)', re.IGNORECASE)
    rgba_pattern = re.compile(r'rgba\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*[\d.]+\s*\)', re.IGNORECASE)
    hsl_pattern = re.compile(r'hsl\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})%?\s*,\s*(\d{1,3})%?\s*\)', re.IGNORECASE)
    hsla_pattern = re.compile(r'hsla\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})%?\s*,\s*(\d{1,3})%?\s*,\s*[\d.]+\s*\)', re.IGNORECASE)
    
    colors = []
    
    for match in hex_pattern.findall(html):
        if len(match) == 4:
            c = '#' + ''.join(ch * 2 for ch in match[1:])
            colors.append(c)
        else:
            colors.append(match.lower())
    
    for m in rgb_pattern.finditer(html):
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if r <= 255 and g <= 255 and b <= 255:
            colors.append(f'#{r:02x}{g:02x}{b:02x}')
    
    for m in rgba_pattern.finditer(html):
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if r <= 255 and g <= 255 and b <= 255:
            colors.append(f'#{r:02x}{g:02x}{b:02x}')
    
    for m in hsl_pattern.finditer(html):
        h, s, l = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if h <= 360 and s <= 100 and l <= 100:
            r, g, b = hsl_to_rgb(h, s / 100, l / 100)
            colors.append(f'#{r:02x}{g:02x}{b:02x}')
    
    for m in hsla_pattern.finditer(html):
        h, s, l = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if h <= 360 and s <= 100 and l <= 100:
            r, g, b = hsl_to_rgb(h, s / 100, l / 100)
            colors.append(f'#{r:02x}{g:02x}{b:02x}')
    
    logger.info(f'Extracted {len(colors)} raw color values')
    
    seen = set()
    unique = []
    ignored_bw = 0
    for c in colors:
        if c in ('#000000', '#ffffff', '#fff', '#000'):
            ignored_bw += 1
            continue
        if c not in seen:
            seen.add(c)
            unique.append(c)
            
    if ignored_bw > 0:
        logger.info(f'Ignored {ignored_bw} black/white colors')
    
    logger.info(f'Found {len(unique)} unique colors (after filtering)')
    
    return unique[:20]


def hsl_to_rgb(h, s, l):
    if s == 0:
        return int(l * 255), int(l * 255), int(l * 255)
    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q
    h_norm = h / 360
    def hue_to_rgb(t):
        if t < 0: t += 1
        if t > 1: t -= 1
        if t < 1/6: return p + (q - p) * 6 * t
        if t < 1/2: return q
        if t < 2/3: return p + (q - p) * (2/3 - t) * 6
        return p
    r = int(hue_to_rgb(h_norm + 1/3) * 255)
    g = int(hue_to_rgb(h_norm) * 255)
    b = int(hue_to_rgb(h_norm - 1/3) * 255)
    return r, g, b





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

            elif self.path == '/api/extract-colors':
                body = self.read_body()
                url = str(body.get('url', '')).strip()
                if not url:
                    return self.send_json(400, {'error': 'url required'})
                logger.info(f'Extracting colors from: {url}')
                try:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Cache-Control', 'no-cache')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    
                    def send_progress(message):
                        self.wfile.write(f'data: {json.dumps({"type": "progress", "message": message})}\n\n'.encode())
                    
                    html, base_url = fetch_url(url)
                    send_progress('Parsing HTML…')
                    full_content = fetch_linked_resources(html, base_url, send_progress)
                    colors = extract_colors(full_content)
                    logger.info(f'Extraction complete: {len(colors)} colors')
                    self.wfile.write(f'data: {json.dumps({"colors": colors})}\n\n'.encode())
                except Exception as e:
                    logger.error(f'Error extracting colors: {e}')
                    self.wfile.write(f'data: {json.dumps({"error": str(e)})}\n\n'.encode())

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
