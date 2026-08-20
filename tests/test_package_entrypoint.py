import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from excaliflow.installer import doctor, install_skill, resolve_target


ROOT = Path(__file__).resolve().parents[1]


class PackageEntrypointTests(unittest.TestCase):
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
            self.assertFalse(any("__pycache__" in str(path) for path in target.rglob("*")))
            _, ready = doctor("agy", workspace=root)
            self.assertTrue(ready)

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
