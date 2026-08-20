import subprocess
import sys
import unittest
from pathlib import Path


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

