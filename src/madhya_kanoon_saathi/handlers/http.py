"""Minimal HTTP entry point for Cloud Run (DEC-088): stdlib ``ThreadingHTTPServer`` on ``$PORT``.

Cloud Run terminates TLS and forwards plain HTTP to the port in ``$PORT`` (default 8080; container
contract, docs.cloud.google.com/run/docs/container-contract, read 2026-11-21). Each service has
one POST endpoint (``/``); ``GET /healthz`` answers 200 once the process is serving. Handlers get
the request headers with lower-cased names and the raw body, and return (status, body).
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PostHandler = Callable[[Mapping[str, str], bytes], tuple[int, bytes]]
MAX_BODY = 1_000_000  # Telegram updates and Pub/Sub pushes are a few KB


def make_server(post: PostHandler, port: int, host: str = "0.0.0.0") -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self._send(200 if self.path == "/healthz" else 404, b"")

        def do_POST(self) -> None:
            if self.path != "/":
                self._send(404, b"")
                return
            size = int(self.headers.get("Content-Length") or 0)
            if size > MAX_BODY:
                self._send(413, b"")
                return
            body = self.rfile.read(size)
            headers = {k.lower(): v for k, v in self.headers.items()}
            try:
                status, out = post(headers, body)
            except Exception:  # never leak details; the handler logs what it can
                status, out = 500, b""
            self._send(status, out)

        def _send(self, status: int, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return  # default access log prints client addresses; Cloud Run logs requests itself

    return ThreadingHTTPServer((host, port), Handler)


def serve(post: PostHandler) -> None:
    make_server(post, int(os.environ.get("PORT", "8080"))).serve_forever()
