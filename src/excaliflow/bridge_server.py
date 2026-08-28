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
ATLAS_MANIFEST = "atlas-bridge.json"
AIOS_BRIDGE_URL = "http://127.0.0.1:8585/health"


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
    manifest = root / ".excaliflow" / ATLAS_MANIFEST
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
                "upstream_url": DEFAULT_UPSTREAM,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest


def load_bridge_config(project_dir: str | Path) -> dict:
    """Load and validate only ExcaliFlow's own bridge manifest."""
    manifest = Path(project_dir).resolve() / ".excaliflow" / ATLAS_MANIFEST
    try:
        raw = json.loads(manifest.read_text(encoding="utf-8"))
        if raw.get("bridge_kind") != "excaliflow_gemini_proxy":
            raise ValueError("bridge_kind must be excaliflow_gemini_proxy")
        health_url = _loopback_url(str(raw["health_url"]))
        completion_url = _loopback_url(str(raw["completion_url"]))
        upstream_url = _loopback_url(str(raw.get("upstream_url") or DEFAULT_UPSTREAM))
        port = urlparse(health_url).port
        if port is None or urlparse(completion_url).port != port:
            raise ValueError("health_url and completion_url must use the same explicit port")
    except OSError as error:
        raise ValueError(f"Atlas Bridge manifest is unavailable: {manifest}") from error
    except (KeyError, TypeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"Atlas Bridge manifest is invalid: {error}") from error
    return {"manifest": manifest, "port": port, "health_url": health_url, "completion_url": completion_url, "upstream_url": upstream_url}


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


def _endpoint_ready(url: str, timeout_seconds: float = 0.8) -> bool:
    """Return true only for an explicit successful local HTTP health response."""
    try:
        with urllib.request.urlopen(_loopback_url(url), timeout=timeout_seconds) as response:
            return response.status == 200
    except (OSError, urllib.error.HTTPError, ValueError):
        return False


def bridge_status(project_dir: str | Path, *, upstream_url: str = DEFAULT_UPSTREAM, port: int = DEFAULT_PORT) -> dict:
    """Diagnose Atlas, its upstream, and the optional AIOS bridge without mutation."""
    root = Path(project_dir).resolve()
    manifest = root / ".excaliflow" / ATLAS_MANIFEST
    manifest_ready = False
    bridge_url = f"http://127.0.0.1:{port}/health"
    manifest_problem = ""
    if manifest.is_file():
        try:
            config = load_bridge_config(root)
            bridge_url = config["health_url"]
            manifest_ready = True
        except ValueError as error:
            manifest_problem = str(error)
    upstream = _loopback_url(upstream_url)
    upstream_ready = _upstream_ready(upstream)
    bridge_ready = _endpoint_ready(bridge_url) if manifest_ready else False
    aios_bridge_ready = _endpoint_ready(AIOS_BRIDGE_URL)
    if not manifest_ready:
        next_action = "Create the project manifest with: excaliflow bridge init --dir <project>."
    elif not upstream_ready:
        next_action = "Start Gemini Web2API on 127.0.0.1:8081, then rerun: excaliflow bridge doctor."
    elif not bridge_ready:
        next_action = "Start the Atlas Bridge, then rerun: excaliflow bridge doctor."
    else:
        next_action = "Ready: refresh Atlas and ask a question."
    return {
        "project": str(root),
        "manifest": str(manifest),
        "manifest_ready": manifest_ready,
        "manifest_problem": manifest_problem,
        "upstream_url": upstream,
        "upstream_ready": upstream_ready,
        "bridge_url": bridge_url,
        "bridge_ready": bridge_ready,
        "aios_bridge_url": AIOS_BRIDGE_URL,
        "aios_bridge_ready": aios_bridge_ready,
        "next_action": next_action,
    }


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
