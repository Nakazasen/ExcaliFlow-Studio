"""A loopback-only Atlas bridge that forwards to a local OpenAI-compatible AI source."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8788
DEFAULT_UPSTREAM = "http://127.0.0.1:8081/v1"


def _loopback_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Atlas Bridge upstream must be a loopback HTTP URL.")
    return value.rstrip("/")


def initialize_bridge(project_dir: str | Path, *, port: int = DEFAULT_PORT) -> Path:
    """Create a project-local Atlas Bridge manifest without overwriting one."""
    if not 1 <= port <= 65535:
        raise ValueError("Bridge port must be between 1 and 65535.")
    root = Path(project_dir).resolve()
    if not root.is_dir():
        raise ValueError(f"Codebase directory does not exist: {root}")
    manifest = root / ".excaliflow" / "ide-bridge.json"
    if manifest.exists():
        raise FileExistsError(f"Bridge manifest already exists: {manifest}")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "name": "ExcaliFlow Atlas Bridge",
                "bridge_kind": "excaliflow_gemini_proxy",
                "health_url": f"http://127.0.0.1:{port}/health",
                "completion_url": f"http://127.0.0.1:{port}/v1/chat/completions",
                "model": "gemini-3.6-flash",
                "external_processing": True,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest


def _response(handler: BaseHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _upstream_ready(upstream_url: str, timeout_seconds: float = 0.8) -> bool:
    try:
        with urllib.request.urlopen(f"{upstream_url}/models", timeout=timeout_seconds) as response:
            return response.status == 200
    except (OSError, urllib.error.HTTPError):
        return False


def create_bridge_server(upstream_url: str = DEFAULT_UPSTREAM, *, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    """Create, but do not start, a local Atlas Bridge HTTP server for tests or CLI."""
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Atlas Bridge may bind only to a loopback host.")
    upstream = _loopback_url(upstream_url)

    class AtlasBridgeHandler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: object) -> None:
            return

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/health":
                _response(self, {"error": "not found"}, 404)
                return
            if not _upstream_ready(upstream):
                _response(self, {"status": "unavailable", "upstream": "Gemini Web2API is not ready."}, 503)
                return
            _response(self, {"status": "ok", "service": "excaliflow_atlas_bridge", "upstream": "gemini-web2api"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/v1/chat/completions":
                _response(self, {"error": "not found"}, 404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            request_body = self.rfile.read(length)
            request = urllib.request.Request(
                f"{upstream}/chat/completions",
                data=request_body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    raw = response.read()
                    status = response.status
            except urllib.error.HTTPError as error:
                raw = error.read() or json.dumps({"error": {"message": error.reason}}).encode("utf-8")
                status = error.code
            except OSError as error:
                _response(self, {"error": {"message": f"Gemini Web2API is not reachable: {error}"}}, 503)
                return
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    return ThreadingHTTPServer((host, port), AtlasBridgeHandler)


def serve_bridge(upstream_url: str = DEFAULT_UPSTREAM, *, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Run the bridge until interrupted by its owner."""
    server = create_bridge_server(upstream_url, host=host, port=port)
    print(f"ExcaliFlow Atlas Bridge listening on http://{host}:{server.server_port}")
    print(f"Forwarding only to local upstream: {_loopback_url(upstream_url)}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
