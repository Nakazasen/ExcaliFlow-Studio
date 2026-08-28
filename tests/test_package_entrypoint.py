import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from excaliflow.installer import doctor, doctor_issues, install_skill, repository_root, resolve_target


ROOT = Path(__file__).resolve().parents[1]


class PackageEntrypointTests(unittest.TestCase):
    def test_package_version_matches_version_receipt_and_pyproject(self):
        import excaliflow

        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(excaliflow.__version__, (ROOT / "VERSION").read_text(encoding="utf-8").strip())
        self.assertEqual(excaliflow.__version__, metadata["project"]["version"])

    def test_repository_root_resolves_editable_install_direct_url(self):
        class EditableDistribution:
            @staticmethod
            def read_text(name):
                self.assertEqual(name, "direct_url.json")
                return '{"dir_info":{"editable":true},"url":"' + ROOT.as_uri() + '"}'

        with patch("excaliflow.installer.metadata.distribution", return_value=EditableDistribution()):
            self.assertEqual(repository_root(), ROOT)

    def test_package_cli_exposes_the_generator_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "excaliflow.cli", "--help"],
            cwd=ROOT,
            env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")},
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--editorial-out", result.stdout)

    def test_installer_copies_a_portable_skill_without_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = ROOT
            target = resolve_target("agy", workspace=root)
            install_skill(target, source=source)
            self.assertTrue((target / "SKILL.md").is_file())
            self.assertTrue((target / "scripts" / "generate_diagram.py").is_file())
            self.assertTrue((target / "scripts" / "explore_codebase.py").is_file())
            self.assertTrue((target / "scripts" / "Open-ExcaliFlow.cmd").is_file())
            self.assertTrue((target / "src" / "excaliflow" / "explorer.py").is_file())
            self.assertTrue((target / "docs" / "atlas-gemini-web2api.md").is_file())
            self.assertFalse(any("__pycache__" in str(path) for path in target.rglob("*")))
            result = subprocess.run(
                [sys.executable, str(target / "scripts" / "explore_codebase.py"), "ask", "--dir", str(source), "--question", "What is main?"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Source-backed answer", result.stdout)
            _, ready = doctor("agy", workspace=root)
            self.assertTrue(ready)
            (target / "assets" / "vendor" / "panzoom.min.js").unlink()
            _, ready = doctor("agy", workspace=root)
            self.assertFalse(ready)
            self.assertIn("missing assets/vendor/panzoom.min.js", doctor_issues(target))

    def test_documented_hosts_resolve_to_exact_user_and_workspace_destinations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            expected_user = {
                "codex": root / ".codex" / "skills" / "excaliflow",
                "claude": root / ".claude" / "skills" / "excaliflow",
                "copilot": root / ".copilot" / "skills" / "excaliflow",
                "gemini": root / ".gemini" / "skills" / "excaliflow",
                "opencode": root / ".config" / "opencode" / "skills" / "excaliflow",
                "kiro": root / ".kiro" / "skills" / "excaliflow",
            }
            for host, expected in expected_user.items():
                self.assertEqual(resolve_target(host, home=root), expected)
            expected_workspace = {
                "agy": root / ".agents" / "skills" / "excaliflow",
                "claude": root / ".claude" / "skills" / "excaliflow",
                "copilot": root / ".github" / "skills" / "excaliflow",
                "gemini": root / ".gemini" / "skills" / "excaliflow",
                "opencode": root / ".opencode" / "skills" / "excaliflow",
                "kiro": root / ".kiro" / "skills" / "excaliflow",
            }
            for host, expected in expected_workspace.items():
                self.assertEqual(resolve_target(host, workspace=root), expected)

    def test_custom_and_unsupported_destinations_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "requires --target"):
            resolve_target("custom")
        with self.assertRaisesRegex(ValueError, "requires --workspace"):
            resolve_target("agy")
