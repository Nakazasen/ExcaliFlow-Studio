import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "installers" / "ExcaliFlow-Setup.ps1"


class WindowsSetupTests(unittest.TestCase):
    def test_noninteractive_custom_install_copies_and_verifies_portable_skill(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "custom" / "excaliflow"
            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(SETUP),
                    "-IDE",
                    "custom",
                    "-Target",
                    str(target),
                    "-Quiet",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(target), result.stdout)
            self.assertTrue((target / "SKILL.md").is_file())
            self.assertTrue((target / "scripts" / "generate_diagram.py").is_file())

    def test_release_builder_creates_a_double_click_bundle(self):
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
            archive = Path(temp) / "ExcaliFlow-Setup-windows.zip"
            self.assertTrue(archive.is_file())
