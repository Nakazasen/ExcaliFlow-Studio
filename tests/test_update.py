import json
import subprocess
import sys
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from zipfile import ZipFile

from excaliflow.update import check_for_update, current_version


ROOT = Path(__file__).resolve().parents[1]


def manifest(version: str = "0.2.0") -> dict:
    return {
        "schema_version": "excaliflow-update/v1",
        "version": version,
        "release_notes_url": f"https://github.com/Nakazasen/ExcaliFlow-Studio/releases/tag/v{version}",
        "asset_url": f"https://github.com/Nakazasen/ExcaliFlow-Studio/releases/download/v{version}/ExcaliFlow-Setup-windows.zip",
    }


class UpdateTests(unittest.TestCase):
    def make_install(self, root: Path, version: str = "0.1.0") -> None:
        (root / "VERSION").write_text(version + "\n", encoding="utf-8")

    def test_newer_manifest_reports_download_and_notes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_install(root)
            result = check_for_update(root, fetch=lambda _url, _timeout: manifest())
            self.assertEqual(result["status"], "update_available")
            self.assertEqual(result["current_version"], "0.1.0")
            self.assertEqual(result["latest_version"], "0.2.0")
            self.assertIn("ExcaliFlow-Setup-windows.zip", result["asset_url"])

    def test_equal_malformed_and_unreachable_manifests_never_claim_update(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_install(root, "0.2.0")
            self.assertEqual(check_for_update(root, fetch=lambda _url, _timeout: manifest())["status"], "up_to_date")
            malformed = check_for_update(root, fetch=lambda _url, _timeout: {"version": "0.3.0"})
            self.assertEqual(malformed["status"], "unavailable")
            unreachable = check_for_update(root, fetch=lambda _url, _timeout: (_ for _ in ()).throw(OSError("offline")))
            self.assertEqual(unreachable["status"], "unavailable")
            self.assertEqual(current_version(root), "0.2.0")

    def test_cli_check_uses_local_http_manifest_and_never_installs(self):
        body = json.dumps(manifest()).encode("utf-8")

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, _format: str, *_args: object) -> None:
                return

            def do_GET(self) -> None:  # noqa: N802
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.make_install(root)
                result = subprocess.run(
                    [sys.executable, "-m", "excaliflow.cli", "update", "check", "--manifest-url", f"http://127.0.0.1:{server.server_port}/update.json", "--root", str(root)],
                    cwd=ROOT,
                    env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")},
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Update available: 0.2.0", result.stdout)
                self.assertIn("Download:", result.stdout)
                self.assertEqual((root / "VERSION").read_text(encoding="utf-8"), "0.1.0\n")
        finally:
            server.shutdown()
            server.server_close()

    def test_release_bundle_and_workflow_include_version_and_manifest(self):
        workflow = (ROOT / ".github" / "workflows" / "release-windows.yml").read_text(encoding="utf-8")
        self.assertIn("VERSION", workflow)
        self.assertIn("update.json", workflow)
        self.assertIn("Release tag does not match VERSION", workflow)
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(ROOT / "installers" / "build-windows-release.ps1"),
                    "-OutputDirectory",
                    temp,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with ZipFile(Path(temp) / "ExcaliFlow-Setup-windows.zip") as bundle:
                self.assertIn("ExcaliFlow-Setup/VERSION", bundle.namelist())
