#!/usr/bin/env python3
"""Lightweight HTTP mock server for System2 update integration tests.

Serves files from a configurable directory, simulating the raw.githubusercontent.com
endpoint. Supports configurable error responses for specific paths.

Usage:
    python3 tests/mock_server.py --root <dir> --port <port> [--fail-path <path>]

The server starts, prints the base URL to stdout, and runs until killed.
"""

import argparse
import json
import os
import signal
import sys
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


class MockHandler(SimpleHTTPRequestHandler):
    """Serve files from a directory, with configurable failures."""

    fail_paths: set = set()
    serve_root: str = "."

    def translate_path(self, path):
        # Strip the branch prefix from the URL path
        # Expected URL format: /main/<file_path>
        stripped = path.strip("/")
        if stripped.startswith("main/"):
            rel_path = stripped[len("main/"):]
        else:
            rel_path = stripped
        return os.path.join(self.serve_root, rel_path)

    def do_GET(self):
        # Check if this path should fail
        for fail_path in self.fail_paths:
            if fail_path in self.path:
                self.send_error(500, f"Simulated failure for {fail_path}")
                return
        super().do_GET()

    def log_message(self, format, *args):
        # Suppress request logs unless DEBUG is set
        if os.environ.get("MOCK_SERVER_DEBUG"):
            super().log_message(format, *args)


def _make_handler(root, fail_paths):
    """Create a handler class with its own state (safe for parallel servers)."""

    class Handler(MockHandler):
        pass

    Handler.serve_root = str(root)
    Handler.fail_paths = fail_paths or set()
    return Handler


def start_server(root, port=0, fail_paths=None):
    """Start the mock server and return (server, base_url)."""
    handler_cls = _make_handler(root, fail_paths)

    server = HTTPServer(("127.0.0.1", port), handler_cls)
    actual_port = server.server_address[1]
    base_url = f"http://127.0.0.1:{actual_port}"

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    return server, base_url


def main():
    parser = argparse.ArgumentParser(description="Mock HTTP server for System2 tests")
    parser.add_argument("--root", required=True, help="Directory to serve files from")
    parser.add_argument("--port", type=int, default=0, help="Port (0 for random)")
    parser.add_argument("--fail-path", action="append", default=[], help="Paths that return 500")
    args = parser.parse_args()

    server, base_url = start_server(args.root, args.port, set(args.fail_path))
    print(base_url, flush=True)

    # Wait for signal
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
