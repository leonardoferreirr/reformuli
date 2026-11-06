#!/usr/bin/env python3
"""Servidor local que imita o cleanUrls da Vercel (/franquia -> franquia.html).

    python3 tools/serve.py 4240
"""
import http.server, os, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(RAIZ), **k)

    def translate_path(self, path):
        p = super().translate_path(path)
        if not os.path.exists(p) and os.path.exists(p + ".html"):
            return p + ".html"
        return p

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *a):
        pass


port = int(sys.argv[1]) if len(sys.argv) > 1 else 4240
http.server.ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
