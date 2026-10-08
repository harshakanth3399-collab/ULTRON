from http.server import BaseHTTPRequestHandler
import json

try:
    import sqlite3
    has_sqlite = True
except Exception as e:
    has_sqlite = False
    sqlite_err = str(e)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'has_sqlite': has_sqlite,
            'err': sqlite_err if not has_sqlite else ''
        }).encode('utf-8'))
